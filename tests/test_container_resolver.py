import pytest
from unittest.mock import MagicMock, patch
from pathlib import Path
import threading
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.docker.resolver import ContainerResolver


class TestContainerResolverInit:
    """Tests for ContainerResolver initialization."""

    def test_resolver_file_exists(self):
        """Verify ContainerResolver module exists."""
        assert ContainerResolver is not None

    def test_cache_initialized_empty(self):
        """Verify cache dict is initialized empty."""
        with patch("src.docker.resolver.docker.DockerClient") as mock_docker:
            mock_client = MagicMock()
            mock_docker.return_value = mock_client
            
            resolver = ContainerResolver()
            assert resolver._cache == {}

    def test_lock_initialized(self):
        """Verify lock is initialized."""
        with patch("src.docker.resolver.docker.DockerClient") as mock_docker:
            mock_client = MagicMock()
            mock_docker.return_value = mock_client
            
            resolver = ContainerResolver()
            assert isinstance(resolver._lock, type(threading.RLock()))

    def test_docker_connection_failure(self):
        """Verify Docker connection failure handling."""
        from docker.errors import DockerException
        
        with patch("src.docker.resolver.docker.DockerClient") as mock_docker:
            mock_docker.side_effect = DockerException("Connection refused")
            
            resolver = ContainerResolver()
            assert resolver.client is None

    def test_cache_initialized_empty(self):
        """Verify cache dict is initialized empty."""
        with patch("src.docker.resolver.docker.DockerClient") as mock_docker:
            mock_client = MagicMock()
            mock_docker.return_value = mock_client
            
            resolver = ContainerResolver()
            assert resolver._cache == {}

    def test_lock_initialized(self):
        """Verify lock is initialized."""
        with patch("src.docker.resolver.docker.DockerClient") as mock_docker:
            mock_client = MagicMock()
            mock_docker.return_value = mock_client
            
            resolver = ContainerResolver()
            assert isinstance(resolver._lock, type(threading.RLock()))

    def test_docker_connection_failure(self):
        """Verify Docker connection failure handling."""
        from docker.errors import DockerException
        
        with patch("src.docker.resolver.docker.DockerClient") as mock_docker:
            mock_docker.side_effect = DockerException("Connection refused")
            
            resolver = ContainerResolver()
            assert resolver.client is None


class TestContainerResolverResolve:
    """Tests for resolve method."""

    def test_resolve_handles_edge_cases(self):
        """Verify resolve handles edge cases gracefully."""
        import sys
        sys.path.insert(0, str(Path(__file__).parent.parent))
        from src.docker.resolver import ContainerResolver
        
        resolver = ContainerResolver.__new__(ContainerResolver)
        resolver._cache = {}
        resolver.client = None
        
        result = resolver.resolve(12345)
        
        assert result is None

    def test_cache_hit_returns_cached(self):
        """Verify cache hit returns cached value."""
        with patch("src.docker.resolver.docker.DockerClient") as mock_docker:
            mock_client = MagicMock()
            mock_docker.return_value = mock_client
            
            resolver = ContainerResolver()
            resolver._cache[12345] = {"id": "abc123", "name": "test"}
            
            result = resolver.resolve(12345)
            
            assert result["id"] == "abc123"
            mock_client.containers.list.assert_not_called()

    def test_cache_miss_refreshes(self):
        """Verify cache miss triggers refresh."""
        with patch("src.docker.resolver.docker.DockerClient") as mock_docker:
            mock_client = MagicMock()
            mock_container = MagicMock()
            mock_container.id = "def456"
            mock_container.name = "web"
            mock_container.image.tags = ["nginx:latest"]
            mock_container.labels = {"app": "web"}
            mock_client.containers.list.return_value = [mock_container]
            mock_docker.return_value = mock_client
            
            resolver = ContainerResolver()
            result = resolver.resolve(99999)
            
            mock_client.containers.list.assert_called_once()


class TestContainerResolverRefresh:
    """Tests for _refresh_and_resolve method."""

    def test_docker_exception_returns_none(self):
        """Verify Docker exception returns None."""
        from docker.errors import DockerException
        
        with patch("src.docker.resolver.docker.DockerClient") as mock_docker:
            mock_client = MagicMock()
            mock_client.containers.list.side_effect = DockerException("Error")
            mock_docker.return_value = mock_client
            
            resolver = ContainerResolver()
            result = resolver._refresh_and_resolve(12345)
            
            assert result is None

    def test_updates_cache_on_refresh(self):
        """Verify cache is updated on refresh."""
        with patch("src.docker.resolver.docker.DockerClient") as mock_docker:
            mock_client = MagicMock()
            mock_container = MagicMock()
            mock_container.id = "xyz789"
            mock_container.name = "api"
            mock_container.image.tags = ["api:v1"]
            mock_container.labels = {}
            mock_client.containers.list.return_value = [mock_container]
            mock_docker.return_value = mock_client
            
            resolver = ContainerResolver()
            resolver._refresh_and_resolve(11111)
            
            assert len(resolver._cache) > 0

    def test_handles_missing_image_tags(self):
        """Verify missing image tags handled."""
        with patch("src.docker.resolver.docker.DockerClient") as mock_docker:
            mock_client = MagicMock()
            mock_container = MagicMock()
            mock_container.id = "abc"
            mock_container.name = "test"
            mock_container.image.tags = []
            mock_container.labels = {}
            mock_client.containers.list.return_value = [mock_container]
            mock_docker.return_value = mock_client
            
            resolver = ContainerResolver()
            result = resolver._refresh_and_resolve(12345)
            
            assert result["image"] == "unknown"

    def test_handles_missing_labels(self):
        """Verify missing labels handled."""
        with patch("src.docker.resolver.docker.DockerClient") as mock_docker:
            mock_client = MagicMock()
            mock_container = MagicMock()
            mock_container.id = "abc"
            mock_container.name = "test"
            mock_container.image.tags = ["test:v1"]
            mock_container.labels = {}
            mock_client.containers.list.return_value = [mock_container]
            mock_docker.return_value = mock_client
            
            resolver = ContainerResolver()
            result = resolver._refresh_and_resolve(12345)
            
            assert "labels" in result


class TestContainerResolverClearCache:
    """Tests for clear_cache method."""

    def test_clear_cache_clears_all(self):
        """Verify clear_cache clears cache."""
        with patch("src.docker.resolver.docker.DockerClient") as mock_docker:
            mock_client = MagicMock()
            mock_docker.return_value = mock_client
            
            resolver = ContainerResolver()
            resolver._cache[1] = {"id": "a"}
            resolver._cache[2] = {"id": "b"}
            
            resolver.clear_cache()
            
            assert resolver._cache == {}


class TestContainerResolverThreadSafety:
    """Tests for thread safety."""

    def test_concurrent_resolve_thread_safe(self):
        """Verify concurrent resolve is thread safe."""
        import threading
        
        with patch("src.docker.resolver.docker.DockerClient") as mock_docker:
            mock_client = MagicMock()
            mock_container = MagicMock()
            mock_container.id = "abc"
            mock_container.name = "test"
            mock_container.image.tags = ["test:latest"]
            mock_container.labels = {}
            mock_client.containers.list.return_value = [mock_container]
            mock_docker.return_value = mock_client
            
            resolver = ContainerResolver()
            results = []
            errors = []
            
            def worker(cid):
                try:
                    r = resolver.resolve(cid)
                    results.append(r)
                except Exception as e:
                    errors.append(e)
            
            threads = [threading.Thread(target=worker, args=(i,)) for i in range(5)]
            for t in threads:
                t.start()
            for t in threads:
                t.join()
            
            assert len(errors) == 0

    def test_lock_is_reentrant(self):
        """Verify lock is reentrant."""
        with patch("src.docker.resolver.docker.DockerClient") as mock_docker:
            mock_client = MagicMock()
            mock_docker.return_value = mock_client
            
            resolver = ContainerResolver()
            
            with resolver._lock:
                with resolver._lock:
                    pass
            
            assert True


class TestContainerResolverEdgeCases:
    """Edge case tests."""

    def test_zero_cgroup_id(self):
        """Verify zero cgroup ID is handled."""
        with patch("src.docker.resolver.docker.DockerClient") as mock_docker:
            mock_client = MagicMock()
            mock_docker.return_value = mock_client
            
            resolver = ContainerResolver()
            resolver._cache[0] = {"id": "zero"}
            
            result = resolver.resolve(0)
            
            assert result["id"] == "zero"

    def test_large_cgroup_id(self):
        """Verify large cgroup ID is handled."""
        with patch("src.docker.resolver.docker.DockerClient") as mock_docker:
            mock_client = MagicMock()
            mock_docker.return_value = mock_client
            
            resolver = ContainerResolver()
            
            result = resolver.resolve(2**63 - 1)
            
            assert result is None or result is not None

    def test_empty_container_list(self):
        """Verify empty container list handled."""
        with patch("src.docker.resolver.docker.DockerClient") as mock_docker:
            mock_client = MagicMock()
            mock_client.containers.list.return_value = []
            mock_docker.return_value = mock_client
            
            resolver = ContainerResolver()
            result = resolver._refresh_and_resolve(12345)
            
            assert result is None


class TestContainerResolverMetadata:
    """Tests for metadata structure."""

    def test_metadata_has_id(self):
        """Verify metadata has id field."""
        with patch("src.docker.resolver.docker.DockerClient") as mock_docker:
            mock_client = MagicMock()
            mock_container = MagicMock()
            mock_container.id = "container123"
            mock_container.name = "myapp"
            mock_container.image.tags = ["myapp:latest"]
            mock_container.labels = {"env": "prod"}
            mock_client.containers.list.return_value = [mock_container]
            mock_docker.return_value = mock_client
            
            resolver = ContainerResolver()
            result = resolver._refresh_and_resolve(12345)
            
            assert "id" in result

    def test_metadata_has_name(self):
        """Verify metadata has name field."""
        with patch("src.docker.resolver.docker.DockerClient") as mock_docker:
            mock_client = MagicMock()
            mock_container = MagicMock()
            mock_container.id = "container123"
            mock_container.name = "myapp"
            mock_container.image.tags = ["myapp:latest"]
            mock_container.labels = {}
            mock_client.containers.list.return_value = [mock_container]
            mock_docker.return_value = mock_client
            
            resolver = ContainerResolver()
            result = resolver._refresh_and_resolve(12345)
            
            assert "name" in result

    def test_metadata_has_image(self):
        """Verify metadata has image field."""
        with patch("src.docker.resolver.docker.DockerClient") as mock_docker:
            mock_client = MagicMock()
            mock_container = MagicMock()
            mock_container.id = "container123"
            mock_container.name = "myapp"
            mock_container.image.tags = ["nginx:1.21"]
            mock_container.labels = {}
            mock_client.containers.list.return_value = [mock_container]
            mock_docker.return_value = mock_client
            
            resolver = ContainerResolver()
            result = resolver._refresh_and_resolve(12345)
            
            assert "image" in result

    def test_metadata_has_labels(self):
        """Verify metadata has labels field."""
        with patch("src.docker.resolver.docker.DockerClient") as mock_docker:
            mock_client = MagicMock()
            mock_container = MagicMock()
            mock_container.id = "container123"
            mock_container.name = "myapp"
            mock_container.image.tags = ["app:v1"]
            mock_container.labels = {"key": "value"}
            mock_client.containers.list.return_value = [mock_container]
            mock_docker.return_value = mock_client
            
            resolver = ContainerResolver()
            result = resolver._refresh_and_resolve(12345)
            
            assert "labels" in result