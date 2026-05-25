import sys
import threading
import pytest
from contextlib import contextmanager
from unittest.mock import MagicMock, patch

from internal.container.resolver import ContainerResolver


@contextmanager
def _fake_docker_module(client=None):
    """Inject a fake ``docker`` module into ``sys.modules`` so the lazy
    ``import docker`` inside ``ContainerResolver.__init__`` resolves to
    our mock without touching the real Docker SDK or daemon.

    Yields the mocked ``docker`` module so tests can configure
    ``from_env`` behavior on it.
    """
    real_docker = sys.modules.get("docker")
    fake = MagicMock(name="docker")
    if client is not None:
        fake.from_env.return_value = client
    sys.modules["docker"] = fake
    try:
        yield fake
    finally:
        if real_docker is not None:
            sys.modules["docker"] = real_docker
        else:
            sys.modules.pop("docker", None)


def _make_resolver_without_docker():
    """Build a resolver instance with the Docker client forced to None.

    Bypasses ``__init__`` so we don't hit the real Docker daemon during
    unit tests, but still gets all the attributes ``__init__`` would set.
    """
    r = ContainerResolver.__new__(ContainerResolver)
    r.target_label = None
    r._cache = {}
    r._lock = threading.RLock()
    r._docker = None
    return r


class TestContainerResolverInit:
    """Tests for ContainerResolver initialization."""

    def test_resolver_class_importable(self):
        assert ContainerResolver is not None

    def test_init_without_docker_does_not_raise(self):
        """If the Docker SDK cannot connect, init should still succeed
        and leave ``_docker`` as None."""
        with _fake_docker_module() as fake:
            fake.from_env.side_effect = Exception("no daemon")
            resolver = ContainerResolver()
        assert resolver._docker is None
        assert resolver._cache == {}

    def test_init_with_docker_stores_client(self):
        """When docker.from_env succeeds, the client is stored on ``_docker``."""
        fake_client = MagicMock()
        with _fake_docker_module(client=fake_client):
            resolver = ContainerResolver()
        assert resolver._docker is fake_client

    def test_cache_initialized_empty(self):
        with _fake_docker_module() as fake:
            fake.from_env.side_effect = Exception("no daemon")
            resolver = ContainerResolver()
        assert resolver._cache == {}

    def test_lock_is_reentrant(self):
        resolver = _make_resolver_without_docker()
        with resolver._lock:
            with resolver._lock:
                pass  # would deadlock if not reentrant

    def test_target_label_from_env(self):
        with _fake_docker_module() as fake:
            fake.from_env.side_effect = Exception("no daemon")
            resolver = ContainerResolver(target_label="app=web")
        assert resolver.target_label == "app=web"


class TestContainerResolverResolve:
    """Tests for the ``resolve`` method."""

    def test_resolve_without_docker_returns_none(self):
        resolver = _make_resolver_without_docker()
        assert resolver.resolve(12345) is None

    def test_cache_hit_returns_cached_no_docker_call(self):
        resolver = _make_resolver_without_docker()
        resolver._docker = MagicMock()
        resolver._cache[12345] = {"id": "abc123", "name": "test"}

        result = resolver.resolve(12345)

        assert result == {"id": "abc123", "name": "test"}
        resolver._docker.containers.list.assert_not_called()

    def test_cache_miss_triggers_docker_lookup(self):
        resolver = _make_resolver_without_docker()
        resolver._docker = MagicMock()
        resolver._docker.containers.list.return_value = []

        resolver.resolve(99999)

        resolver._docker.containers.list.assert_called_once()

    def test_docker_list_exception_returns_none(self):
        resolver = _make_resolver_without_docker()
        resolver._docker = MagicMock()
        resolver._docker.containers.list.side_effect = RuntimeError("boom")

        assert resolver.resolve(12345) is None


class TestExtractCgroupInode:
    """Tests for the static helper that parses /proc/<pid>/cgroup output."""

    def test_extracts_docker_id_from_cgroup_v2(self):
        container_id = "0123456789abcdef" * 4  # 64 hex chars
        cgroup_data = f"0::/system.slice/docker-{container_id}.scope\n"
        result = ContainerResolver._extract_cgroup_inode(cgroup_data)
        assert result is not None

    def test_returns_none_for_non_docker(self):
        cgroup_data = "0::/user.slice/user-1000.slice/session-1.scope\n"
        assert ContainerResolver._extract_cgroup_inode(cgroup_data) is None

    def test_returns_none_for_empty(self):
        assert ContainerResolver._extract_cgroup_inode("") is None


class TestMatchesLabel:
    """Tests for the ``_matches_label`` helper."""

    def test_no_target_label_matches_everything(self):
        resolver = _make_resolver_without_docker()
        container = MagicMock(labels={"any": "thing"})
        assert resolver._matches_label(container) is True

    def test_key_value_label_matches(self):
        resolver = _make_resolver_without_docker()
        resolver.target_label = "app=web"
        container = MagicMock(labels={"app": "web"})
        assert resolver._matches_label(container) is True

    def test_key_value_label_mismatch(self):
        resolver = _make_resolver_without_docker()
        resolver.target_label = "app=web"
        container = MagicMock(labels={"app": "db"})
        assert resolver._matches_label(container) is False

    def test_key_only_label_present(self):
        resolver = _make_resolver_without_docker()
        resolver.target_label = "monitored"
        container = MagicMock(labels={"monitored": ""})
        assert resolver._matches_label(container) is True

    def test_key_only_label_absent(self):
        resolver = _make_resolver_without_docker()
        resolver.target_label = "monitored"
        container = MagicMock(labels={"other": "x"})
        assert resolver._matches_label(container) is False


class TestClearCache:
    def test_clear_cache_empties_cache(self):
        resolver = _make_resolver_without_docker()
        resolver._cache[1] = {"id": "a"}
        resolver._cache[2] = {"id": "b"}

        resolver.clear_cache()

        assert resolver._cache == {}


class TestThreadSafety:
    def test_concurrent_resolve_no_errors(self):
        """Many threads calling resolve() concurrently shouldn't raise."""
        resolver = _make_resolver_without_docker()
        errors = []

        def worker(cid):
            try:
                resolver.resolve(cid)
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=worker, args=(i,)) for i in range(20)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert errors == []
