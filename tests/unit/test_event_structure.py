import re
import pytest
from pathlib import Path

ROOT_DIR = Path(__file__).parent.parent.parent; EBPF_DIR = ROOT_DIR / "drivers" / "ebpf"
TRACER_FILE = EBPF_DIR / "src" / "tracer.bpf.c"


class TestEventStructure:
    """Tests for event structure definition validation."""

    @pytest.fixture
    def tracer_content(self):
        """Load tracer.bpf.c content."""
        return TRACER_FILE.read_text()

    def test_event_struct_exists(self, tracer_content):
        """Verify event struct is defined."""
        assert "struct event" in tracer_content, "event struct not found"
        assert "{" in tracer_content, "event struct body not found"

    def test_event_struct_has_pid_field(self, tracer_content):
        """Verify event struct has pid field."""
        assert re.search(r'__u32\s+pid', tracer_content), "pid field (__u32) not found in event struct"

    def test_event_struct_has_tgid_field(self, tracer_content):
        """Verify event struct has tgid field."""
        assert re.search(r'__u32\s+tgid', tracer_content), "tgid field (__u32) not found in event struct"

    def test_event_struct_has_cgroup_id_field(self, tracer_content):
        """Verify event struct has cgroup_id field."""
        assert re.search(r'__u64\s+cgroup_id', tracer_content), "cgroup_id field (__u64) not found"

    def test_event_struct_has_op_type_field(self, tracer_content):
        """Verify event struct has op_type field."""
        assert re.search(r'__u32\s+op_type', tracer_content), "op_type field (__u32) not found in event struct"

    def test_event_struct_has_comm_field(self, tracer_content):
        """Verify event struct has comm field (process name)."""
        assert re.search(r'char\s+comm\[', tracer_content), "comm field (char array) not found in event struct"

    def test_event_struct_comm_array_size(self, tracer_content):
        """Verify comm field has reasonable size (16 bytes)."""
        match = re.search(r'char\s+comm\[(\d+)\]', tracer_content)
        assert match, "comm array size not found"
        size = int(match.group(1))
        assert size >= 16, "comm array should be at least 16 bytes for task name"

    def test_event_struct_has_filename_field(self, tracer_content):
        """Verify event struct has filename field."""
        assert re.search(r'char\s+filename\[', tracer_content), "filename field not found in event struct"

    def test_event_struct_filename_array_size(self, tracer_content):
        """Verify filename array is large enough for paths."""
        match = re.search(r'char\s+filename\[(\d+)\]', tracer_content)
        assert match, "filename array size not found"
        size = int(match.group(1))
        assert size >= 256, "filename array should be at least 256 bytes for paths"

    def test_event_struct_alignment(self, tracer_content):
        """Verify event struct uses proper types for alignment."""
        assert "__u32" in tracer_content, "Should use fixed-width integer types"
        assert "__u64" in tracer_content, "Should use fixed-width integer types"

    def test_event_used_in_trace_openat(self, tracer_content):
        """Verify event struct is used in trace_openat function."""
        assert "struct event *e" in tracer_content, "Event pointer not created in trace_openat"

    def test_event_fields_populated(self, tracer_content):
        """Verify event fields are populated in trace_openat_exit."""
        assert "e.pid" in tracer_content or "e->pid" in tracer_content, "pid not assigned to event"
        assert "e.op_type" in tracer_content or "e->op_type" in tracer_content, "op_type not assigned"
        assert "e.fd" in tracer_content or "e->fd" in tracer_content, "fd not assigned"
        assert "e.comm" in tracer_content or "e->comm" in tracer_content, "comm not assigned"

    def test_op_type_open_value(self, tracer_content):
        """Verify OP_OPEN is used for openat events."""
        assert "OP_OPEN" in tracer_content, "OP_OPEN constant not used"