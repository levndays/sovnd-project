import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

from core.graph.builder import ProvenanceGraphBuilder


class TestProvenanceGraphBuilder:
    """Tests for ProvenanceGraphBuilder."""

    def test_add_event_creates_process_node(self):
        """Test add_event creates a process node when pid is provided."""
        builder = ProvenanceGraphBuilder()
        event = {"pid": 123, "comm": "bash", "filename": "", "syscall_id": 2}
        
        builder.add_event(event)
        
        assert builder.graph.has_node("proc_123")
        assert builder.graph.nodes["proc_123"]["type"] == "process"
        assert builder.graph.nodes["proc_123"]["pid"] == 123

    def test_add_event_creates_file_node(self):
        """Test add_event creates a file node when filename is provided."""
        builder = ProvenanceGraphBuilder()
        event = {"pid": 123, "comm": "bash", "filename": "/etc/passwd", "syscall_id": 2}
        
        builder.add_event(event)
        
        assert builder.graph.has_node("file_/etc/passwd")
        assert builder.graph.nodes["file_/etc/passwd"]["type"] == "file"
        assert builder.graph.nodes["file_/etc/passwd"]["path"] == "/etc/passwd"

    def test_add_event_creates_edge(self):
        """Test add_event creates an edge from process to file."""
        builder = ProvenanceGraphBuilder()
        event = {"pid": 123, "comm": "bash", "filename": "/etc/passwd", "syscall_id": 2}
        
        builder.add_event(event)
        
        assert builder.graph.has_edge("proc_123", "file_/etc/passwd")
        assert builder.graph.edges[("proc_123", "file_/etc/passwd")]["syscall"] == 2

    def test_add_event_duplicate_process(self):
        """Test duplicate process nodes are not duplicated."""
        builder = ProvenanceGraphBuilder()
        events = [
            {"pid": 123, "comm": "bash", "filename": "/etc/passwd", "syscall_id": 2},
            {"pid": 123, "comm": "bash", "filename": "/etc/shadow", "syscall_id": 2},
        ]
        
        for event in events:
            builder.add_event(event)
        
        assert len([n for n in builder.graph.nodes() if n.startswith("proc_")]) == 1
        assert len(list(builder.graph.edges())) == 2

    def test_add_event_missing_filename(self):
        """Test add_event with no filename creates no file node or edge."""
        builder = ProvenanceGraphBuilder()
        event = {"pid": 123, "comm": "bash", "filename": "", "syscall_id": 2}
        
        builder.add_event(event)
        
        assert builder.graph.has_node("proc_123")
        assert len([n for n in builder.graph.nodes() if n.startswith("file_")]) == 0

    def test_get_process_subgraph_existing(self):
        """Test get_process_subgraph returns neighborhood for existing PID."""
        builder = ProvenanceGraphBuilder()
        events = [
            {"pid": 123, "comm": "bash", "filename": "/etc/passwd", "syscall_id": 2},
            {"pid": 123, "comm": "bash", "filename": "/var/log/syslog", "syscall_id": 2},
        ]
        for event in events:
            builder.add_event(event)
        
        subgraph = builder.get_process_subgraph(123)
        
        assert subgraph.has_node("proc_123")
        assert len(subgraph.nodes()) == 3

    def test_get_process_subgraph_missing(self):
        """Test get_process_subgraph returns empty graph for non-existent PID."""
        builder = ProvenanceGraphBuilder()
        
        subgraph = builder.get_process_subgraph(999)
        
        assert len(subgraph.nodes()) == 0

    def test_serialized_graph_format(self):
        """Test serialized returns valid node_link_data format."""
        builder = ProvenanceGraphBuilder()
        event = {"pid": 123, "comm": "bash", "filename": "/etc/passwd", "syscall_id": 2}
        builder.add_event(event)
        
        serialized = builder.serialized()
        
        assert "nodes" in serialized
        assert "links" in serialized or "edges" in serialized

    def test_clear_graph(self):
        """Test clear removes all nodes and edges."""
        builder = ProvenanceGraphBuilder()
        event = {"pid": 123, "comm": "bash", "filename": "/etc/passwd", "syscall_id": 2}
        builder.add_event(event)
        
        builder.clear()
        
        assert len(builder.graph.nodes()) == 0
        assert len(builder.graph.edges()) == 0