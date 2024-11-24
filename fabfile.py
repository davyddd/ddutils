from fabric.api import local

SERVICE_NAME = 'ddutils'


def build():
    local(f'docker-compose build {SERVICE_NAME}')


def _run_command_container(command):
    container_id = local(f"docker ps | grep '{SERVICE_NAME}' | awk '{{ print $1 }}' | head -n 1", capture=True)
    if container_id:
        local(f'docker exec -it {container_id} bash -c "{command}"')
    else:
        local(f'docker-compose run --rm {SERVICE_NAME} bash -c "{command}"')


def linters():
    _run_command_container(
        "ruff . --config ruff.toml --fix && echo 'Ruff check completed'; "
        'ruff format . --config ruff.toml; '
        'mypy --config mypy.toml;'
    )


def tests():
    _run_command_container('pytest')


def shell():
    _run_command_container('python -m IPython')


def bash():
    _run_command_container('bash')


def kill():
    local('docker kill $(docker ps -q)')
