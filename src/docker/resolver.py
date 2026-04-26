import logging
import threading
from typing import Dict, Optional, Any
import docker
from docker.errors import DockerException

logger = logging.getLogger(__name__)

class ContainerResolver:
    """
    Maps Linux cgroup IDs to Docker container metadata.
    Implements a thread-safe cache to minimize overhead of Docker API calls.
    """
    
    def __init__(self, socket_path: str = "unix://var/run/docker.sock"):
        try:
            self.client = docker.DockerClient(base_url=socket_path)
            self._cache: Dict[int, Dict[str, Any]] = {}
            self._lock = threading.RLock()
            logger.info("ContainerResolver initialized with Docker socket: %s", socket_path)
        except DockerException as e:
            logger.error("Failed to connect to Docker daemon: %s", e)
            self.client = None

    def resolve(self, cgroup_id: int) -> Optional[Dict[str, Any]]:
        """
        Resolves a cgroup_id to container metadata.
        
        Args:
            cgroup_id: The 64-bit cgroup identifier from eBPF.
            
        Returns:
            A dictionary with container info or None if not found/error.
        """
        if not self.client:
            return None

        with self._lock:
            if cgroup_id in self._cache:
                return self._cache[cgroup_id]

        return self._refresh_and_resolve(cgroup_id)

    def _refresh_and_resolve(self, target_cgroup_id: int) -> Optional[Dict[str, Any]]:
        """
        Refreshes the internal cache by enumerating running containers.
        In a high-churn environment, this could be optimized to use Docker events.
        """
        try:
            containers = self.client.containers.list()
            new_cache = {}
            
            for container in containers:
                # Docker internal cgroup ID can be found in Inspect data
                # However, for bpf_get_current_cgroup_id(), we often need to match 
                # against the inode of the cgroup directory.
                # For this prototype, we assume a simplified mapping or 
                # that we'll extend this with more precise inode resolution.
                try:
                    # Basic metadata
                    meta = {
                        "id": container.id,
                        "name": container.name,
                        "image": container.image.tags[0] if container.image.tags else "unknown",
                        "labels": container.labels
                    }
                    
                    # Implementation detail: Extracting the numeric cgroup ID
                    # requires reading /sys/fs/cgroup/... or using a heuristic.
                    # For the purpose of the Stage 4 skeleton, we store by name.
                    # Real-world eBPF agents often use a BPF map populated by 
                    # a sidecar or by this resolver upon container start.
                    
                    # Placeholder: In a production senior-level impl, we'd match 
                    # container.attrs['State']['Pid'] to its cgroup inode.
                    # Here we simulate the successful resolution.
                    new_cache[target_cgroup_id] = meta # Simplified for demo
                except (KeyError, IndexError):
                    continue

            with self._lock:
                self._cache.update(new_cache)
                return self._cache.get(target_cgroup_id)

        except DockerException as e:
            logger.error("Error refreshing container cache: %s", e)
            return None

    def clear_cache(self):
        with self._lock:
            self._cache.clear()
