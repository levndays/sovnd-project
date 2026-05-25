"""End-to-end-ish integration tests.

Covers:
  - eBPF object build (requires clang + bpftool + libbpf)
  - Generated skeleton header sanity
  - Python bridge lifecycle with the C loader mocked
  - Loader exported symbols (via the ctypes interface)
"""

import os
import queue
import shutil
import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from drivers.ebpf.bridge import EBPFAgent, Event


ROOT_DIR = Path(__file__).parent.parent.parent
EBPF_DIR = ROOT_DIR / "drivers" / "ebpf"


def _have(tool: str) -> bool:
    return shutil.which(tool) is not None


def _libbpf_present() -> bool:
    try:
        return subprocess.run(
            ["pkg-config", "--exists", "libbpf"],
            capture_output=True,
        ).returncode == 0
    except FileNotFoundError:
        return False


requires_build_tools = pytest.mark.skipif(
    not (_have("clang") and _have("bpftool") and _libbpf_present()),
    reason="clang, bpftool, or libbpf-dev not available",
)


# ── eBPF build ───────────────────────────────────────────────────────


class TestBuildIntegration:
    """The eBPF Makefile produces tracer.bpf.o, tracer.skel.h, and
    libloader.so at the root of drivers/ebpf/. These tests run a real
    build — they're skipped when the toolchain isn't installed.
    """

    @requires_build_tools
    def test_full_build_produces_all_artifacts(self):
        subprocess.run(["make", "clean"], cwd=EBPF_DIR, check=True)

        result = subprocess.run(
            ["make", "all"],
            cwd=EBPF_DIR,
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, f"Build failed: {result.stderr}"

        for artifact in ("tracer.bpf.o", "tracer.skel.h", "libloader.so"):
            assert (EBPF_DIR / artifact).exists(), \
                f"Expected artifact {artifact} not found after make all"

    @requires_build_tools
    def test_build_creates_libloader_so(self):
        subprocess.run(["make", "all"], cwd=EBPF_DIR, check=True)
        assert (EBPF_DIR / "libloader.so").exists()

    @requires_build_tools
    def test_build_creates_skeleton_header(self):
        subprocess.run(["make", "all"], cwd=EBPF_DIR, check=True)
        assert (EBPF_DIR / "tracer.skel.h").exists()

    @requires_build_tools
    def test_skeleton_header_has_bpf_prog_definitions(self):
        subprocess.run(["make", "all"], cwd=EBPF_DIR, check=True)
        content = (EBPF_DIR / "tracer.skel.h").read_text()

        for sym in ("tracer_bpf__open", "tracer_bpf__load",
                    "tracer_bpf__attach", "tracer_bpf__destroy"):
            assert sym in content, f"Missing {sym} in skeleton"

    @requires_build_tools
    def test_clean_removes_all_build_artifacts(self):
        subprocess.run(["make", "all"], cwd=EBPF_DIR, check=True)
        subprocess.run(["make", "clean"], cwd=EBPF_DIR, check=True)

        try:
            for artifact in ("tracer.bpf.o", "tracer.skel.h", "libloader.so"):
                assert not (EBPF_DIR / artifact).exists(), \
                    f"{artifact} should have been removed by make clean"
        finally:
            # tracer.skel.h is tracked in git (so the project can be
            # inspected without bpftool installed). Regenerate it so
            # we don't leave the working tree dirty.
            subprocess.run(["make", "tracer.skel.h"], cwd=EBPF_DIR, check=True)


# ── Python bridge ↔ ctypes loader contract ───────────────────────────


class TestPythonAgentIntegration:

    def test_ebpf_agent_can_import(self):
        assert EBPFAgent is not None
        assert Event is not None

    def test_ebpf_agent_initialization(self):
        """Agent init doesn't load the shared library — that happens
        lazily inside ``start()`` — so we can construct an agent
        even with a bogus path."""
        agent = EBPFAgent(lib_path="/nonexistent/libloader.so")
        assert agent is not None
        assert agent._polling is False
        assert agent.lib is None

    def test_agent_event_structure_matches_c_event(self):
        assert hasattr(Event, "_fields_")
        fields = dict(Event._fields_)

        # Match the C definition in drivers/ebpf/include/maps.bpf.h
        import ctypes
        assert fields["pid"] == ctypes.c_uint32
        assert fields["tgid"] == ctypes.c_uint32
        assert fields["cgroup_id"] == ctypes.c_uint64
        assert fields["op_type"] == ctypes.c_uint32
        assert fields["fd"] == ctypes.c_uint32
        assert fields["fd_type"] == ctypes.c_uint32
        assert fields["bytes"] == ctypes.c_uint64
        assert "comm" in fields
        assert "filename" in fields


class TestLoaderAgentIntegration:

    def test_loader_exports_required_functions(self, tmp_path):
        """When the agent calls start(), it binds three C symbols on
        the loaded library: start_loader, poll_events, stop_loader."""
        fake_so = tmp_path / "libloader.so"
        fake_so.write_bytes(b"")
        agent = EBPFAgent(lib_path=str(fake_so))

        with patch("drivers.ebpf.bridge.ctypes.CDLL") as mock_cdll:
            mock_lib = MagicMock()
            mock_lib.start_loader.return_value = 0
            mock_cdll.return_value = mock_lib
            agent.start()

            for sym in ("start_loader", "poll_events", "stop_loader"):
                assert hasattr(agent.lib, sym)
        agent.stop()

    def test_agent_callback_pushed_into_queue(self):
        """The C library invokes ``_c_callback(ctx, data, size)`` —
        the agent copies into the queue, where ``get_event`` drains."""
        import ctypes
        agent = EBPFAgent(lib_path="/nonexistent.so")
        e = Event()
        e.pid = 9001
        ptr = ctypes.cast(ctypes.pointer(e), ctypes.c_void_p)
        agent._c_callback(None, ptr, ctypes.sizeof(Event))

        result = agent.get_event(timeout=0.05)
        assert result is not None
        assert result["pid"] == 9001


class TestEndToEndSimulation:

    def test_agent_lifecycle_simulation(self, tmp_path):
        fake_so = tmp_path / "libloader.so"
        fake_so.write_bytes(b"")
        agent = EBPFAgent(lib_path=str(fake_so))

        with patch("drivers.ebpf.bridge.ctypes.CDLL") as mock_cdll:
            mock_lib = MagicMock()
            mock_lib.start_loader.return_value = 0
            mock_cdll.return_value = mock_lib

            assert agent._polling is False
            agent.start()
            assert agent._polling is True
            agent.stop()
            assert agent._polling is False
            mock_lib.stop_loader.assert_called_once()

    def test_multiple_start_stop_cycles(self, tmp_path):
        fake_so = tmp_path / "libloader.so"
        fake_so.write_bytes(b"")
        agent = EBPFAgent(lib_path=str(fake_so))

        with patch("drivers.ebpf.bridge.ctypes.CDLL") as mock_cdll:
            mock_lib = MagicMock()
            mock_lib.start_loader.return_value = 0
            mock_cdll.return_value = mock_lib

            for _ in range(3):
                agent.start()
                agent.stop()

            assert mock_lib.start_loader.call_count == 3
            assert mock_lib.stop_loader.call_count == 3


class TestErrorHandlingIntegration:

    def test_agent_handles_missing_library(self):
        import ctypes
        with pytest.raises(OSError):
            ctypes.CDLL("/nonexistent/path/libloader.so")

    def test_agent_start_raises_on_loader_failure(self, tmp_path):
        fake_so = tmp_path / "libloader.so"
        fake_so.write_bytes(b"")
        agent = EBPFAgent(lib_path=str(fake_so))

        with patch("drivers.ebpf.bridge.ctypes.CDLL") as mock_cdll:
            mock_lib = MagicMock()
            mock_lib.start_loader.return_value = 1  # nonzero = failure
            mock_cdll.return_value = mock_lib
            with pytest.raises(RuntimeError) as exc:
                agent.start()
            assert "Failed to start eBPF loader" in str(exc.value)


# ── build environment sanity ─────────────────────────────────────────


class TestBuildEnvironmentIntegration:

    def test_clang_available(self):
        assert _have("clang"), "clang not in PATH"

    def test_bpftool_available(self):
        assert _have("bpftool"), "bpftool not in PATH"

    def test_libbpf_available(self):
        assert _libbpf_present(), "libbpf-dev not installed"
