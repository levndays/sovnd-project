import re
import pytest
from pathlib import Path

ROOT_DIR = Path(__file__).parent.parent.parent; EBPF_DIR = ROOT_DIR / "drivers" / "ebpf"
TRACER_FILE = EBPF_DIR / "src" / "tracer.bpf.c"


class TestTracepointHooks:
    """Tests for eBPF tracepoint hook validation."""

    @pytest.fixture
    def tracer_content(self):
        """Load tracer.bpf.c content."""
        return TRACER_FILE.read_text()

    def test_tracer_file_exists(self):
        """Verify tracer.bpf.c exists."""
        assert TRACER_FILE.exists(), "tracer.bpf.c not found"

    def test_includes_required_headers(self, tracer_content):
        """Verify required headers are included."""
        required_headers = ["vmlinux.h", "bpf/bpf_helpers.h", "bpf/bpf_tracing.h", "maps.bpf.h"]
        for header in required_headers:
            assert header in tracer_content, f"Required header {header} not included"

    def test_license_defined(self, tracer_content):
        """Verify GPL license is defined."""
        assert "LICENSE" in tracer_content, "LICENSE not defined"
        assert "GPL" in tracer_content, "GPL license not set"

    def test_trace_openat_hook_exists(self, tracer_content):
        """Verify tracepoint for openat syscall is defined."""
        assert "sys_enter_openat" in tracer_content, "sys_enter_openat tracepoint not found"
        assert "trace_openat" in tracer_content, "trace_openat handler function not found"

    def test_trace_close_hook_exists(self, tracer_content):
        """Verify tracepoint for close syscall is defined."""
        assert "sys_enter_close" in tracer_content, "sys_enter_close tracepoint not found"
        assert "trace_close" in tracer_content, "trace_close handler function not found"

    def test_openat_tracepoint_sec_format(self, tracer_content):
        """Verify openat tracepoint has correct SEC() format."""
        pattern = r'SEC\("tracepoint/syscalls/sys_enter_openat"\)'
        assert re.search(pattern, tracer_content), "Incorrect SEC format for openat tracepoint"

    def test_close_tracepoint_sec_format(self, tracer_content):
        """Verify close tracepoint has correct SEC() format."""
        pattern = r'SEC\("tracepoint/syscalls/sys_enter_close"\)'
        assert re.search(pattern, tracer_content), "Incorrect SEC format for close tracepoint"

    def test_trace_openat_returns_int(self, tracer_content):
        """Verify trace_openat function returns int."""
        pattern = r'int\s+trace_openat\s*\('
        assert re.search(pattern, tracer_content), "trace_openat should return int"

    def test_trace_close_returns_int(self, tracer_content):
        """Verify trace_close function returns int."""
        pattern = r'int\s+trace_close\s*\('
        assert re.search(pattern, tracer_content), "trace_close should return int"

    def test_trace_openat_context_param(self, tracer_content):
        """Verify trace_openat has correct context parameter."""
        assert "struct trace_event_raw_sys_enter" in tracer_content, "Missing trace_event_raw_sys_enter context"

    def test_bpf_get_current_pid_tgid_used(self, tracer_content):
        """Verify bpf_get_current_pid_tgid is used."""
        assert "bpf_get_current_pid_tgid" in tracer_content, "bpf_get_current_pid_tgid not used"

    def test_bpf_get_current_cgroup_id_used(self, tracer_content):
        """Verify bpf_get_current_cgroup_id is used."""
        assert "bpf_get_current_cgroup_id" in tracer_content, "bpf_get_current_cgroup_id not used"

    def test_bpf_get_current_comm_used(self, tracer_content):
        """Verify bpf_get_current_comm is used."""
        assert "bpf_get_current_comm" in tracer_content, "bpf_get_current_comm not used"

    def test_ringbuf_reserve_used(self, tracer_content):
        """Verify ring buffer reserve is used."""
        assert "bpf_ringbuf_reserve" in tracer_content, "bpf_ringbuf_reserve not used"

    def test_ringbuf_submit_used(self, tracer_content):
        """Verify ring buffer submit is used."""
        assert "bpf_ringbuf_submit" in tracer_content, "bpf_ringbuf_submit not used"

    def test_proc_metrics_lookup(self, tracer_content):
        """Verify the per-process stats map (renamed from proc_metrics
        to proc_stats during refactor) is referenced from the tracer."""
        assert "bpf_map_lookup_elem" in tracer_content, "bpf_map_lookup_elem not used"
        assert "proc_stats" in tracer_content, "proc_stats map not referenced"

    def test_proc_metrics_update(self, tracer_content):
        """Verify proc_metrics map update is used."""
        assert "bpf_map_update_elem" in tracer_content, "bpf_map_update_elem not used"