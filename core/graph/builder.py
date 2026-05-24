"""Provenance-graph builder (§2.2, §3.2 component 6).

Constructs a directed graph ``G = (V, E)`` where vertices are
processes / file resources and edges represent syscall interactions.
Used for lateral-movement and ransomware-pattern detection.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import networkx as nx

from core.config import get_settings, Settings

logger = logging.getLogger(__name__)


class ProvenanceGraphBuilder:
    """In-memory directed provenance graph."""

    def __init__(self, settings: Optional[Settings] = None):
        cfg = settings or get_settings()
        self._graph = nx.DiGraph()
        self._hi_conn_thresh = cfg.graph_high_connectivity_nodes
        self._bulk_thresh     = cfg.graph_bulk_file_ops_nodes
        logger.info("ProvenanceGraphBuilder initialised")

    # ── public API ───────────────────────────────────────────

    def add_event(self, event: Dict[str, Any]) -> None:
        """Ingest a single eBPF event into the graph."""
        pid      = event.get("pid")
        comm     = event.get("comm", "unknown")
        filename = str(event.get("filename") or "")
        syscall  = event.get("op_type") or event.get("syscall_id")

        proc_node = f"proc_{pid}"
        if not self._graph.has_node(proc_node):
            self._graph.add_node(proc_node, type="process", pid=pid, comm=comm)

        if filename:
            res_node = f"file_{filename}"
            if not self._graph.has_node(res_node):
                self._graph.add_node(res_node, type="file", path=filename)
            self._graph.add_edge(
                proc_node, res_node,
                syscall=syscall,
                timestamp=datetime.now(timezone.utc).isoformat(),
            )

    def heuristics(self, pid: int, event: Dict[str, Any]) -> List[str]:
        """Evaluate structural heuristics on the current subgraph.

        Returns a list of heuristic tags (e.g. ``high_connectivity``)
        for the scoring engine.
        """
        result: List[str] = []
        sub = self.get_process_subgraph(pid)

        if sub.number_of_nodes() > self._hi_conn_thresh:
            result.append("high_connectivity")

        fname = str(event.get("filename") or "")
        if any(fname.startswith(p) for p in ("/etc", "/root", "/var/run")):
            result.append("sensitive_access")

        fd_type = event.get("fd_type")
        op_type = event.get("op_type")

        # bulk file ops → potential ransomware
        if op_type in (1, 2) and fd_type == 1 and sub.number_of_nodes() > self._bulk_thresh:
            result.append("mass_file_ops")

        # pipe usage → potential fileless malware
        if fd_type == 3:
            result.append("pipe_usage")

        return result

    def get_process_subgraph(self, pid: int) -> nx.DiGraph:
        """Return the ego-network of *pid* as a subgraph."""
        proc_node = f"proc_{pid}"
        if not self._graph.has_node(proc_node):
            return nx.DiGraph()
        nodes = [proc_node] + list(self._graph.neighbors(proc_node))
        return self._graph.subgraph(nodes)

    def serialized(self) -> Dict[str, Any]:
        """Serialise the full graph to the node-link JSON format."""
        return nx.node_link_data(self._graph)

    def clear(self) -> None:
        self._graph.clear()

