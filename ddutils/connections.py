from collections.abc import Callable, Hashable, Mapping
from typing import Any, Generic, TypeVar

from ddutils.scoped_registry import ScopedRegistry

# The name a connection is registered under and selected by, like Django's `using` alias
ConnectionAliasT = TypeVar('ConnectionAliasT', bound=Hashable)
# The object a registry holds for a connection: a pooled client, a session
ConnectionT = TypeVar('ConnectionT')
# The context manager the factory opens on the chosen registry
ConnectionManagerT = TypeVar('ConnectionManagerT')


class ConnectionManager(Generic[ConnectionT]):
    """
    Default connection manager: hands out the connection of the registry's current scope and releases nothing on exit.

    The connection is created on first use via `registry.set()` and kept for the life of its scope,
    typically a process, since a client is itself a connection pool (ClickHouse, Redis, a Kafka producer). Databases
    with transactions need their own connection manager on top of the registry, e.g. a unit of work that begins,
    commits and closes a session on exit.
    """

    def __init__(self, registry: ScopedRegistry[ConnectionT]) -> None:
        self._registry = registry

    async def __aenter__(self) -> ConnectionT:
        return await self._registry.set()

    async def __aexit__(self, exc_type: type[BaseException] | None, exc_value: BaseException | None, traceback: Any) -> None:
        return None


class ConnectionManagerFactory(Generic[ConnectionAliasT, ConnectionT, ConnectionManagerT]):
    """
    Resolves a connection alias to its registry and opens a connection manager on it, like Django's `using`.

    `connection_manager_class` is the context manager opened on the chosen registry: `ConnectionManager` by
    default, a project class for anything that needs setup and teardown around the connection (transactions):

        clickhouse = ConnectionManagerFactory(client_registries, default=ClickhouseAlias.PRIMARY)
        atomic = ConnectionManagerFactory(session_registries, default=PostgresAlias.PRIMARY, connection_manager_class=Atomic)

        async with clickhouse() as client: ...
        async with atomic(alias=PostgresAlias.REPLICA) as session: ...
        await clickhouse.close()  # on shutdown
    """

    def __init__(
        self,
        registries: Mapping[ConnectionAliasT, ScopedRegistry[ConnectionT]],
        default: ConnectionAliasT,
        connection_manager_class: Callable[[ScopedRegistry[ConnectionT]], ConnectionManagerT] = ConnectionManager,  # type: ignore[assignment]
    ) -> None:
        if default not in registries:
            raise ValueError(f'Default connection {default!r} is not among the registries')
        self.registries = registries
        self.default = default
        self.connection_manager_class = connection_manager_class

    def registry(self, alias: Hashable | None = None) -> ScopedRegistry[ConnectionT]:
        """The registry of `alias`, or of the default connection; `Hashable` because `Adapter.alias` is untyped."""
        alias = self.default if alias is None else alias
        if alias not in self.registries:
            raise KeyError(f'Unknown connection {alias!r}; expected one of {list(self.registries)!r}')
        return self.registries[alias]  # type: ignore[index]

    def __call__(self, alias: Hashable | None = None) -> ConnectionManagerT:
        return self.connection_manager_class(self.registry(alias))

    async def close(self) -> None:
        """
        Clears every registry for the current scope, calling the connection's destructor: the shutdown hook of
        a process-scoped client (a pool, a producer with a buffer to flush). A registry without a connection in
        the current scope is left alone, so the hook is safe to call for aliases that were never used.
        """
        for registry in self.registries.values():
            await registry.clear()


__all__ = ('ConnectionManager', 'ConnectionManagerFactory')
