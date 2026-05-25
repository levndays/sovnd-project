"""Cgroup-id → container metadata resolver.

The eBPF tracer captures ``bpf_get_current_cgroup_id()`` for each event,
which is the **cgroup v2 inode** of the calling process. To turn that
into Docker container metadata we:

  1. ask the Docker SDK for the labeled containers we care about,
  2. read each container's init PID's ``/proc/<pid>/cgroup`` to learn
     the cgroup hierarchy path it lives under,
  3. ``stat()`` that path under ``/sys/fs/cgroup`` to read the real
     inode the kernel exposes,
  4. cache ``inode → metadata`` so subsequent lookups are O(1).

The earlier implementation tried to use a 32-bit hash of the container
ID as a stand-in for the inode; that never matches the value eBPF
emits, so resolution silently always returned ``None``.
"""

from __future__ import annotations

import logging
import os
import re
import threading
from pathlib import Path
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

# /proc/<pid>/cgroup line forms:
#   cgroup v2:  0::/system.slice/docker-<64-hex>.scope
#   cgroup v1:  <controller>:<subsystem>:/docker/<64-hex>
CGROUP_PATH_RE = re.compile(r"^[\d]+::?(?P<path>/.*)$")
CGROUP_V2_MOUNT = Path("/sys/fs/cgroup")


class ContainerResolver:
    """Maps eBPF-supplied cgroup inodes to Docker container metadata."""

    TARGET_LABEL_KEY = "sovnd.monitor"

    def __init__(self, target_label: Optional[str] = None):
        self.target_label = target_label or os.environ.get("TARGET_LABEL")
        self._cache: Dict[int, Dict[str, Any]] = {}
        self._lock = threading.RLock()
        self._docker = None

        try:
            import docker
            self._docker = docker.from_env()
            logger.info("ContainerResolver: Docker SDK connected")
        except Exception as e:  # pragma: no cover - environment-dependent
            logger.warning("ContainerResolver: Docker unavailable (%s)", e)

    # ── public API ───────────────────────────────────────────────────

    def resolve(self, cgroup_id: int) -> Optional[Dict[str, Any]]:
        """Resolve a cgroup v2 inode to container metadata, or ``None``.

        Hot path: cache lookup. On miss, scan the docker daemon, populate
        the cache for every labeled container, and return the match (if
        any).
        """
        with self._lock:
            if cgroup_id in self._cache:
                return self._cache[cgroup_id]

        if not self._docker:
            return None

        self._refresh_cache()

        with self._lock:
            return self._cache.get(cgroup_id)

    def find_target_cgroup_inode(self) -> Optional[int]:
        """Look up the cgroup inode of the (single) target container.

        Used at agent startup to populate the eBPF ``filter_config`` map
        so the kernel side only emits events from the monitored
        container's cgroup.
        """
        if not self._docker:
            return None
        self._refresh_cache()
        # The cache key is the inode; pick the first matching entry.
        with self._lock:
            for inode in self._cache:
                return inode
        return None

    def clear_cache(self) -> None:
        with self._lock:
            self._cache.clear()

    # ── internals ────────────────────────────────────────────────────

    def _refresh_cache(self) -> None:
        """Populate ``_cache`` with ``{inode: metadata}`` for every
        labeled container currently known to Docker."""
        try:
            containers = self._docker.containers.list()
        except Exception as e:
            logger.error("ContainerResolver: failed to list containers: %s", e)
            return

        for container in containers:
            if not self._matches_label(container):
                continue

            inode = self._container_cgroup_inode(container)
            if inode is None:
                continue

            meta = {
                "id":     container.id[:12],
                "name":   container.name,
                "image":  (container.image.tags[0]
                           if container.image.tags else "unknown"),
                "labels": container.labels,
            }
            with self._lock:
                self._cache[inode] = meta

    def _container_cgroup_inode(self, container) -> Optional[int]:
        """Return the real cgroup v2 inode for ``container``'s init PID."""
        try:
            pid = container.attrs.get("State", {}).get("Pid", 0)
            if pid <= 0:
                return None
            cgroup_data = Path(f"/proc/{pid}/cgroup").read_text()
        except (FileNotFoundError, PermissionError, KeyError) as e:
            logger.debug("ContainerResolver: can't read cgroup for %s: %s",
                         getattr(container, "name", "?"), e)
            return None

        path = self._extract_cgroup_path(cgroup_data)
        if path is None:
            return None

        return self._stat_cgroup_inode(path)

    @staticmethod
    def _extract_cgroup_path(cgroup_data: str) -> Optional[str]:
        """Return the cgroup hierarchy path from a /proc/<pid>/cgroup
        file, preferring the cgroup v2 entry (``0::/...``)."""
        v1_fallback = None
        for line in cgroup_data.strip().splitlines():
            if line.startswith("0::"):
                return line[3:].strip()
            # v1 form: <id>:<controller>:/<path>
            parts = line.split(":", 2)
            if len(parts) == 3 and v1_fallback is None and parts[2]:
                v1_fallback = parts[2].strip()
        return v1_fallback

    @staticmethod
    def _stat_cgroup_inode(cgroup_path: str) -> Optional[int]:
        """``stat()`` the cgroup path under /sys/fs/cgroup; the inode
        number matches what ``bpf_get_current_cgroup_id()`` returns."""
        rel = cgroup_path.lstrip("/")
        full = CGROUP_V2_MOUNT / rel
        try:
            return full.stat().st_ino
        except (FileNotFoundError, PermissionError, OSError) as e:
            logger.debug("ContainerResolver: stat(%s) failed: %s", full, e)
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
