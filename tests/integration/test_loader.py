import re
import pytest
from pathlib import Path

ROOT_DIR = Path(__file__).parent.parent.parent; EBPF_DIR = ROOT_DIR / "drivers" / "ebpf"
LOADER_FILE = EBPF_DIR / "loader" / "loader.c"


class TestLoaderC:
    """Tests for ebpf/loader.c validation."""

    @pytest.fixture
    def loader_content(self):
        """Load loader.c content."""
        return LOADER_FILE.read_text()

    def test_loader_file_exists(self):
        """Verify loader.c exists."""
        assert LOADER_FILE.exists(), "loader.c not found"

    def test_includes_required_headers(self, loader_content):
        """Verify required headers are included."""
        required = ["stdio.h", "stdlib.h", "string.h", "errno.h", "bpf/libbpf.h", "bpf/bpf.h"]
        for header in required:
            assert header in loader_content, f"Required header {header} not included"

    def test_includes_tracer_skeleton(self, loader_content):
        """Verify tracer.skel.h is included."""
        assert 'tracer.skel.h' in loader_content, "tracer.skel.h not included"

    def test_libbpf_print_fn_exists(self, loader_content):
        """Verify libbpf print callback is defined."""
        assert "libbpf_print_fn" in loader_content, "libbpf_print_fn not found"

    def test_libbpf_print_fn_signature(self, loader_content):
        """Verify libbpf_print_fn has correct signature."""
        pattern = r'static\s+int\s+libbpf_print_fn\s*\(\s*enum\s+libbpf_print_level'
        assert re.search(pattern, loader_content), "libbpf_print_fn signature incorrect"

    def test_global_skel_variable(self, loader_content):
        """Verify skeleton global variable is declared."""
        assert "struct tracer_bpf *skel" in loader_content, "Global skel variable not found"

    def test_global_rb_variable(self, loader_content):
        """Verify ring buffer global variable is declared."""
        assert "ring_buffer *rb" in loader_content or "struct ring_buffer *rb" in loader_content, "Global rb variable not found"

    def test_user_callback_global(self, loader_content):
        """Verify user_callback global variable exists."""
        assert "user_callback" in loader_content, "user_callback global not found"

    def test_event_cb_typedef(self, loader_content):
        """Verify event callback typedef is defined."""
        assert "event_cb_t" in loader_content, "event_cb_t typedef not found"

    def test_handle_event_function_exists(self, loader_content):
        """Verify handle_event function exists."""
        assert "handle_event" in loader_content, "handle_event function not found"

    def test_handle_event_calls_callback(self, loader_content):
        """Verify handle_event calls user_callback."""
        assert "user_callback" in loader_content and "handle_event" in loader_content
        assert re.search(r'if\s*\(\s*user_callback\s*\)', loader_content), "user_callback not checked before calling"

    def test_start_loader_function_exists(self, loader_content):
        """Verify start_loader function exists."""
        assert re.search(r'int\s+start_loader\s*\(', loader_content), "start_loader function not found"

    def test_start_loader_sets_libbpf_print(self, loader_content):
        """Verify start_loader sets libbpf print callback."""
        assert "libbpf_set_print" in loader_content, "libbpf_set_print not called"

    def test_start_loader_opens_skeleton(self, loader_content):
        """Verify start_loader opens BPF skeleton."""
        assert "tracer_bpf__open" in loader_content, "tracer_bpf__open not called"

    def test_start_loader_loads_skeleton(self, loader_content):
        """Verify start_loader loads BPF skeleton."""
        assert "tracer_bpf__load" in loader_content, "tracer_bpf__load not called"

    def test_start_loader_attaches_skeleton(self, loader_content):
        """Verify start_loader attaches BPF skeleton."""
        assert "tracer_bpf__attach" in loader_content, "tracer_bpf__attach not called"

    def test_start_loader_creates_ring_buffer(self, loader_content):
        """Verify start_loader creates ring buffer."""
        assert "ring_buffer__new" in loader_content, "ring_buffer__new not called"

    def test_start_loader_checks_ring_buffer(self, loader_content):
        """Verify start_loader checks ring buffer creation."""
        assert re.search(r'if\s*\(\s*!rb\s*\)', loader_content), "Ring buffer NULL check not found"

    def test_poll_events_function_exists(self, loader_content):
        """Verify poll_events function exists."""
        assert re.search(r'int\s+poll_events\s*\(', loader_content), "poll_events function not found"

    def test_poll_events_calls_ring_buffer_poll(self, loader_content):
        """Verify poll_events uses ring_buffer__poll."""
        assert "ring_buffer__poll" in loader_content, "ring_buffer__poll not called"

    def test_stop_loader_function_exists(self, loader_content):
        """Verify stop_loader function exists."""
        assert re.search(r'void\s+stop_loader\s*\(', loader_content), "stop_loader function not found"

    def test_stop_loader_frees_ring_buffer(self, loader_content):
        """Verify stop_loader frees ring buffer."""
        assert "ring_buffer__free" in loader_content, "ring_buffer__free not called"

    def test_stop_loader_destroys_skeleton(self, loader_content):
        """Verify stop_loader destroys skeleton."""
        assert "tracer_bpf__destroy" in loader_content, "tracer_bpf__destroy not called"

    def test_cleanup_label_exists(self, loader_content):
        """Verify cleanup label exists for error handling."""
        assert re.search(r'cleanup:', loader_content), "cleanup label not found"

    def test_error_messages_to_stderr(self, loader_content):
        """Verify error messages go to stderr."""
        assert "fprintf(stderr" in loader_content, "Error messages should use stderr"

    def test_null_check_on_skel_open(self, loader_content):
        """Verify skeleton open result is checked for NULL."""
        assert re.search(r'if\s*\(\s*!skel\s*\)', loader_content), "skel NULL check not found"

    def test_error_return_on_skel_failure(self, loader_content):
        """Verify error return when skeleton open fails."""
        assert re.search(r'return\s+1', loader_content), "Error return value not found"

    def test_callback_assignment_in_start_loader(self, loader_content):
        """Verify user_callback is assigned in start_loader."""
        lines_after_start = loader_content.split("start_loader")[1].split("poll_events")[0]
        assert "user_callback = cb" in lines_after_start, "user_callback not assigned in start_loader"


class TestLoaderMakefile:
    """Tests for Makefile validation related to loader."""

    @pytest.fixture
    def makefile_content(self):
        """Load Makefile content."""
        return (EBPF_DIR / "Makefile").read_text()

    def test_makefile_exists(self):
        """Verify Makefile exists."""
        assert (EBPF_DIR / "Makefile").exists()

    def test_libloader_target_exists(self, makefile_content):
        """Verify libloader.so target exists."""
        assert "libloader.so:" in makefile_content, "libloader.so target not found"

    def test_skeleton_generation_target(self, makefile_content):
        """Verify skeleton generation target exists."""
        assert ".skel.h" in makefile_content, "skeleton target not found"

    def test_bpftool_used_for_skeleton(self, makefile_content):
        """Verify bpftool is used for skeleton generation."""
        assert "bpftool" in makefile_content, "bpftool not used"

    def test_libloader_depends_on_loader_c(self, makefile_content):
        """Verify libloader.so depends on loader.c."""
        assert "loader.c" in makefile_content, "loader.c dependency missing"

    def test_libloader_depends_on_skeleton(self, makefile_content):
        """Verify libloader.so depends on skeleton header."""
        assert "skel.h" in makefile_content, "skeleton header dependency missing"

    def test_clean_removes_so_file(self, makefile_content):
        """Verify clean removes .so files."""
        assert "rm" in makefile_content and ".so" in makefile_content, "clean should remove .so files"