import hashlib
import logging
import random
import time
from abc import ABC, abstractmethod
from collections.abc import Mapping
from dataclasses import dataclass, field, fields
from typing import Any, NamedTuple, Protocol, Self

logger = logging.getLogger(__name__)

DEFAULT_PROPORTION = 0.01

BASE_TTL = 15  # seconds a record is served from the cache before it is re-read
JITTER = 5  # seconds added at random to the TTL, so the readers of a process do not re-read at once
ERROR_TTL = 1  # seconds before the first re-read after a storage error; doubles on every failure up to `base_ttl`

_BUCKETS = 1 << 32


class Stringable(Protocol):
    def __str__(self) -> str: ...


_TRUE_WORDS = frozenset({'true', '1', 'yes', 'on', 't', 'y'})
_FALSE_WORDS = frozenset({'false', '0', 'no', 'off', 'f', 'n'})


def _parse_bool(value: Any) -> bool:
    """A bool from what a storage may hold: a bool, 0 / 1, or a word like `true`, `'1'`, `yes`, `on`."""
    if isinstance(value, bool):
        return value
    if isinstance(value, int) and value in (0, 1):
        return bool(value)
    if isinstance(value, bytes):
        value = value.decode()
    if isinstance(value, str):
        word = value.strip().lower()
        if word in _TRUE_WORDS:
            return True
        if word in _FALSE_WORDS:
            return False
    raise ValueError(f'`enabled` must be a bool, got {value!r}')


def _parse_proportion(value: Any) -> float:
    if isinstance(value, bool) or not isinstance(value, int | float | str):
        raise ValueError(f'`proportion` must be a number in 0..1, got {value!r}')
    try:
        proportion = float(value)
    except ValueError as e:
        raise ValueError(f'`proportion` must be a number in 0..1, got {value!r}') from e
    if not 0 <= proportion <= 1:
        raise ValueError(f'`proportion` must be in 0..1, got {proportion!r}')
    return proportion


@dataclass(frozen=True)
class FeatureFlagRecord:
    """
    What a storage holds for one flag: whether it is on, the proportion of readers that see it and a free-form
    payload. The contract between a storage and `FeatureFlags`; readers see `bool`s and payloads, not records.

    Validated on construction: `enabled` takes a bool or what a storage may hold for one (`1`, `'true'`, `'1'`,
    `'yes'`), `proportion` is a number in 0..1, `payload` a mapping (copied). Anything else is a `ValueError`.
    Storages build records with `from_dict` and write `to_dict`.
    """

    enabled: bool = False
    proportion: float = DEFAULT_PROPORTION
    payload: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, 'enabled', _parse_bool(self.enabled))
        object.__setattr__(self, 'proportion', _parse_proportion(self.proportion))
        if not isinstance(self.payload, Mapping):
            raise ValueError(f'`payload` must be a mapping, got {type(self.payload).__name__}')
        object.__setattr__(self, 'payload', dict(self.payload))

    @classmethod
    def from_dict(cls, data: Any) -> Self:
        """A record from what a storage read; `ValueError` for anything that is not a valid record."""
        if not isinstance(data, Mapping):
            raise ValueError(f'a record must be a mapping, got {type(data).__name__}')
        unknown = set(data) - {f.name for f in fields(cls)}
        if unknown:
            raise ValueError(f'unknown record fields {sorted(unknown)!r}')
        return cls(**data)

    def to_dict(self) -> dict[str, Any]:
        return {'enabled': self.enabled, 'proportion': self.proportion, 'payload': dict(self.payload)}


class FeatureFlagStorageError(Exception):
    """The storage could not answer (connection, timeout, server error); the cause is chained."""


class FeatureFlagStorage(ABC):
    """
    Where the flags live. One flag is one `FeatureFlagRecord` under its name.

    A missing flag is `None`, a malformed one is read as the defaults: only a failure of the storage itself
    raises, as `FeatureFlagStorageError`, so that `FeatureFlags` can keep serving the last known values.
    Implementations: `ddredis.feature_flags.RedisFeatureFlagStorage`, `ddaerospike.feature_flags.AerospikeFeatureFlagStorage`.
    """

    @abstractmethod
    async def get(self, name: str) -> FeatureFlagRecord | None: ...

    @abstractmethod
    async def get_map(self) -> dict[str, FeatureFlagRecord]:
        """Every flag by name."""

    @abstractmethod
    async def put(self, name: str, record: FeatureFlagRecord) -> None:
        """Create or overwrite the flag."""

    @abstractmethod
    async def delete(self, name: str) -> bool:
        """False when there was no such flag."""

    async def rename(self, old_name: str, new_name: str, record: FeatureFlagRecord) -> None:
        """Write the flag under `new_name` and drop `old_name`; atomic where the storage allows it."""
        await self.put(new_name, record)
        await self.delete(old_name)


class _CacheEntry(NamedTuple):
    record: FeatureFlagRecord
    expiration_time: float
    failures: int  # consecutive storage errors behind this entry; 0 when it was read


class FeatureFlags:
    """
    Feature flags read through a `FeatureFlagStorage`, with a per-process cache.

    Each flag is on or off, has a proportion for gradual rollouts and a payload for arbitrary data. Records are
    cached for `base_ttl` plus a random jitter so the storage is not read on every call. While the storage
    fails the last known record (or the defaults, for a flag never read) is served, re-read after `ERROR_TTL`
    and then with an exponential backoff up to `base_ttl`.

    `is_enabled` is the flag's switch and its proportion in one answer: off for everyone when the flag is off,
    on for the `proportion` of the readers when it is on (a kill-switch is a flag with proportion 1.0). With an
    `idempotent_key` (a user id, an account id) the split is repeatable: every call with the same key lands on
    the same side, so a rollout is a consistent group. Without one it is random per call.
    `get_payload` is the flag's payload as stored; its shape is the application's business, parse it there.

    Example:
        feature_flags = FeatureFlags(RedisFeatureFlagStorage(redis_client_factory))

        if await feature_flags.is_enabled('new_checkout'):              # proportion 1.0: on or off for everyone
            ...
        if await feature_flags.is_enabled('new_ranking', user_id):      # on for `proportion` of the users
            ...
        if await feature_flags.is_enabled('email_provider_block'):
            rules = EmailProviderBlockRules.model_validate(await feature_flags.get_payload('email_provider_block'))
    """

    def __init__(self, storage: FeatureFlagStorage, base_ttl: int = BASE_TTL) -> None:
        self.storage = storage
        self.base_ttl = base_ttl
        self._cache: dict[str, _CacheEntry] = {}

    async def is_enabled(self, name: str, idempotent_key: Stringable | None = None) -> bool:
        """
        Whether the flag is on for this reader: the stored switch is on and the reader falls into the
        `proportion`. A missing flag is off. `idempotent_key` (a user id, an account id) makes the split
        repeatable: the key is hashed into a bucket of the flag, so the same key always lands on the same side
        and a rollout is a consistent group, not a coin flip per call. Without a key the decision is random on
        every call.
        """
        record = await self._get_record(name)
        return record.enabled and self._in_proportion(name, idempotent_key, record.proportion)

    async def get_payload(self, name: str) -> Mapping[str, Any]:
        """The payload of the flag as stored, empty for a missing flag; check `is_enabled` first."""
        return (await self._get_record(name)).payload

    @staticmethod
    def _in_proportion(name: str, idempotent_key: Stringable | None, proportion: float) -> bool:
        if idempotent_key is None:
            return random.random() < proportion
        # The flag name is part of the hash, so one user is not in the first N% of every flag at once
        digest = hashlib.blake2b(f'{name}:{idempotent_key}'.encode(), digest_size=4).digest()
        return int.from_bytes(digest, 'big') / _BUCKETS < proportion

    async def _get_record(self, name: str) -> FeatureFlagRecord:
        entry = self._cache.get(name)
        now = time.time()
        if entry is not None and now < entry.expiration_time:
            return entry.record

        try:
            record = await self.storage.get(name)
        except FeatureFlagStorageError as e:
            # Keep serving the last known record (or the defaults) and retry with a backoff
            failures = entry.failures + 1 if entry is not None else 1
            record = entry.record if entry is not None else FeatureFlagRecord()
            ttl = min(ERROR_TTL * 2 ** (failures - 1), self.base_ttl)
            logger.error(
                {
                    'message': 'FEATURE_FLAGS: Storage error, serving the last known record',
                    'flag_name': name,
                    'retry_in': ttl,
                    'error': repr(e.__cause__ or e),
                }
            )
        else:
            failures = 0
            record = record if record is not None else FeatureFlagRecord()
            ttl = self.base_ttl + random.randint(0, JITTER)

        self._cache[name] = _CacheEntry(record, now + ttl, failures)
        return record


__all__ = (
    'BASE_TTL',
    'DEFAULT_PROPORTION',
    'ERROR_TTL',
    'FeatureFlagRecord',
    'FeatureFlagStorage',
    'FeatureFlagStorageError',
    'FeatureFlags',
    'Stringable',
)
