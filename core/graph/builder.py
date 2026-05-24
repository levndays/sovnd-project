import networkx as nx
import logging
from typing import Dict, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

class ProvenanceGraphBuilder:
    """
    Constructs a directed provenance graph (Section 2.2).
    Nodes: Processes, Files, Sockets.
    Edges: Actions (open, read, write).
    """
    
    def __init__(self):
        self.graph = nx.DiGraph()
        logger.info("ProvenanceGraphBuilder initialized.")

    def add_event(self, event: Dict[str, Any]):
        """
        Adds an event to the graph. 
        Event structure: pid, comm, filename, syscall_id, timestamp
        """
        pid = event.get("pid")
        comm = event.get("comm", "unknown")
        filename = event.get("filename", "")
        syscall = event.get("syscall_id")
        
        # Process node
        proc_node = f"proc_{pid}"
        if not self.graph.has_node(proc_node):
            self.graph.add_node(proc_node, type="process", pid=pid, comm=comm)
            
        # Resource node (if applicable)
        if filename:
            res_node = f"file_{filename}"
            if not self.graph.has_node(res_node):
                self.graph.add_node(res_node, type="file", path=filename)
            
            # Add edge representing the action
            self.graph.add_edge(
                proc_node, 
                res_node, 
                syscall=syscall, 
                timestamp=datetime.now().isoformat()
            )

    def get_process_subgraph(self, pid: int) -> nx.DiGraph:
        """
        Returns the neighborhood of a specific process.
        """
        proc_node = f"proc_{pid}"
        if not self.graph.has_node(proc_node):
            return nx.DiGraph()
            
        nodes = [proc_node] + list(self.graph.neighbors(proc_node))
        return self.graph.subgraph(nodes)

    def get_serialized_graph(self) -> Dict[str, Any]:
        """
        Serializes the graph for UI consumption (e.g., cytoscape or d3 format).
        """
        return nx.node_link_data(self.graph)

    def clear(self):
        self.graph.clear()
