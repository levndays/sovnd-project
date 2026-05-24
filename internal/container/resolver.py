import logging
import os
import re
import threading
from typing import Dict, Optional, Any
from pathlib import Path

logger = logging.getLogger(__name__)

# Pattern: 0::/system.slice/docker-<container_id>.scope/...
CGROUP_DOCKER_RE = re.compile(r"docker[-/]([a-f0-9]{64})")


class ContainerResolver:
    """
    Maps Linux cgroup IDs to Docker container metadata per §3.2.
    Uses /proc/<pid>/cgroup for cgroup-to-container correlation.
    """

    TARGET_LABEL_KEY = "sovnd.monitor"

    def __init__(self, target_label: str = None):
        self.target_label = target_label or os.environ.get("TARGET_LABEL")
        self._cache: Dict[int, Dict[str, Any]] = {}
        self._lock = threading.RLock()
        self._docker = None

        try:
            import docker
            self._docker = docker.from_env()
            logger.info("ContainerResolver: Docker SDK connected")
        except Exception as e:
            logger.warning("ContainerResolver: Docker unavailable (%s)", e)

    def resolve(self, cgroup_id: int) -> Optional[Dict[str, Any]]:
        """Resolve a 64-bit cgroup ID to container metadata."""
        with self._lock:
            if cgroup_id in self._cache:
                return self._cache[cgroup_id]

        if not self._docker:
            return None

        result = self._scan_containers(cgroup_id)
        if result:
            with self._lock:
                self._cache[cgroup_id] = result
        return result

    def _scan_containers(self, target_cgroup_id: int) -> Optional[Dict[str, Any]]:
        """Scan running containers and match by cgroup inode."""
        try:
            containers = self._docker.containers.list()
        except Exception as e:
            logger.error("ContainerResolver: failed to list containers: %s", e)
            return None

        for container in containers:
            if not self._matches_label(container):
                continue

            try:
                info = container.attrs
                pid = info.get("State", {}).get("Pid", 0)
                if pid <= 0:
                    continue

                # Read cgroup entries for the container's init PID
                cgroup_path = f"/proc/{pid}/cgroup"
                try:
                    cgroup_data = Path(cgroup_path).read_text()
                except (FileNotFoundError, PermissionError):
                    # Fall back to top-level process in the container
                    top = container.top()
                    if top and top.get("Processes"):
                        pid_str = top["Processes"][0][1]
                        if pid_str.isdigit():
                            try:
                                cgroup_data = Path(f"/proc/{pid_str}/cgroup").read_text()
                            except Exception:
                                continue
                        else:
                            continue
                    else:
                        continue

                # Extract cgroup inode for matching
                container_cgroup_id = self._extract_cgroup_inode(cgroup_data)
                if container_cgroup_id is None:
                    continue

                meta = {
                    "id":    container.id[:12],
                    "name":  container.name,
                    "image": (container.image.tags[0]
                              if container.image.tags else "unknown"),
                    "labels": container.labels,
                }

                # Cache by cgroup inode
                with self._lock:
                    self._cache[container_cgroup_id] = meta

                if container_cgroup_id == target_cgroup_id:
                    return meta

            except Exception as e:
                logger.debug("ContainerResolver: skip %s: %s", container.name, e)
                continue

        return None

    @staticmethod
    def _extract_cgroup_inode(cgroup_data: str) -> Optional[int]:
        """Parse cgroup v1/v2 file to get the cgroup inode."""
        for line in cgroup_data.strip().split("\n"):
            match = CGROUP_DOCKER_RE.search(line)
            if match:
                return int(match.group(1), 16) & 0xFFFFFFFF
        return None

    def _matches_label(self, container) -> bool:
        if not self.target_label:
            return True
        key, _, val = self.target_label.partition("=")
        labels = container.labels or {}
        actual = labels.get(key, "")
        if val:
            return actual == val
        return key in labels

    def clear_cache(self):
        with self._lock:
            self._cache.clear()
