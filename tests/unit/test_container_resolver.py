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


class TestExtractCgroupPath:
    """Tests for the helper that parses /proc/<pid>/cgroup to a path.

    The resolver no longer derives an inode from the container ID hash
    (that value never matched ``bpf_get_current_cgroup_id()``); it
    extracts the cgroup hierarchy path and the caller stats it under
    /sys/fs/cgroup to get the real inode.
    """

    def test_extracts_v2_path(self):
        container_id = "0123456789abcdef" * 4  # 64 hex chars
        cgroup_data = f"0::/system.slice/docker-{container_id}.scope\n"
        path = ContainerResolver._extract_cgroup_path(cgroup_data)
        assert path == f"/system.slice/docker-{container_id}.scope"

    def test_v2_preferred_over_v1(self):
        cgroup_data = (
            "9:memory:/docker/abc\n"
            "0::/system.slice/docker-deadbeef.scope\n"
        )
        path = ContainerResolver._extract_cgroup_path(cgroup_data)
        assert path == "/system.slice/docker-deadbeef.scope"

    def test_falls_back_to_v1(self):
        cgroup_data = "9:memory:/docker/abc\n"
        path = ContainerResolver._extract_cgroup_path(cgroup_data)
        assert path == "/docker/abc"

    def test_returns_none_for_empty(self):
        assert ContainerResolver._extract_cgroup_path("") is None


class TestStatCgroupInode:
    """Tests for the inode-reader helper."""

    def test_returns_none_for_missing_path(self):
        assert ContainerResolver._stat_cgroup_inode("/definitely/not/a/cg") is None

    def test_returns_inode_for_existing_path(self, tmp_path, monkeypatch):
        from internal.container import resolver as resolver_mod
        monkeypatch.setattr(resolver_mod, "CGROUP_V2_MOUNT", tmp_path)
        (tmp_path / "foo").mkdir()
        ino = ContainerResolver._stat_cgroup_inode("/foo")
        assert ino is not None
        assert ino == (tmp_path / "foo").stat().st_ino


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


class TestFindTargetCgroupInode:
    """Tests for the helper that locates the target container's cgroup
    inode at agent startup (used to narrow the eBPF filter)."""

    def test_returns_none_without_docker(self):
        resolver = _make_resolver_without_docker()
        assert resolver.find_target_cgroup_inode() is None

    def test_returns_first_cached_inode(self):
        resolver = _make_resolver_without_docker()
        resolver._docker = MagicMock()
        # Stub _refresh_cache so we don't go through the real
        # /proc + /sys/fs/cgroup lookup chain
        resolver._refresh_cache = lambda: resolver._cache.update(
            {424242: {"id": "abc", "name": "web"}}
        )
        assert resolver.find_target_cgroup_inode() == 424242


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
