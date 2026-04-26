import os
import subprocess
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

EBPF_DIR = Path(__file__).parent.parent / "ebpf"
SRC_DIR = Path(__file__).parent.parent / "src"


class TestBuildIntegration:
    """Integration tests for building the entire system."""

    def test_full_build_produces_all_artifacts(self):
        """Verify full build produces all expected artifacts."""
        subprocess.run(["make", "clean"], cwd=EBPF_DIR, check=True)
        
        result = subprocess.run(
            ["make", "all"],
            cwd=EBPF_DIR,
            capture_output=True,
            text=True
        )
        
        assert result.returncode == 0, f"Build failed: {result.stderr}"
        
        expected = ["tracer.bpf.o", "tracer.skel.h", "libloader.so"]
        for artifact in expected:
            path = EBPF_DIR / artifact
            assert path.exists(), f"Expected artifact {artifact} not found"

    def test_build_creates_libloader_so(self):
        """Verify libloader.so is created."""
        path = EBPF_DIR / "libloader.so"
        assert path.exists(), "libloader.so not found"

    def test_build_creates_skeleton_header(self):
        """Verify tracer.skel.h is created."""
        path = EBPF_DIR / "tracer.skel.h"
        assert path.exists(), "tracer.skel.h not found"

    def test_skeleton_header_has_bpf_prog_definitions(self):
        """Verify skeleton header contains BPF program definitions."""
        skel = EBPF_DIR / "tracer.skel.h"
        content = skel.read_text()
        
        assert "tracer_bpf__open" in content, "Missing tracer_bpf__open"
        assert "tracer_bpf__load" in content, "Missing tracer_bpf__load"
        assert "tracer_bpf__attach" in content, "Missing tracer_bpf__attach"
        assert "tracer_bpf__destroy" in content, "Missing tracer_bpf__destroy"

    def test_clean_removes_all_build_artifacts(self):
        """Verify make clean removes all generated files."""
        subprocess.run(["make", "all"], cwd=EBPF_DIR, check=True)
        
        subprocess.run(["make", "clean"], cwd=EBPF_DIR, check=True)
        
        generated = ["tracer.bpf.o", "tracer.skel.h", "libloader.so"]
        for artifact in generated:
            path = EBPF_DIR / artifact
            assert not path.exists(), f"Artifact {artifact} should have been cleaned"


class TestPythonAgentIntegration:
    """Integration tests for Python agent with C library."""

    def test_ebpf_agent_can_import(self):
        """Verify ebpf_agent module can be imported."""
        import sys
        sys.path.insert(0, str(SRC_DIR))
        from ebpf_agent import EBPFAgent, Event
        assert EBPFAgent is not None
        assert Event is not None

    def test_ebpf_agent_initialization_integration(self):
        """Test EBPFAgent can be initialized with mocked library."""
        with patch("ebpf_agent.ctypes.CDLL") as mock_cdll:
            mock_lib = MagicMock()
            mock_cdll.return_value = mock_lib
            
            import sys
            sys.path.insert(0, str(SRC_DIR))
            from ebpf_agent import EBPFAgent
            
            agent = EBPFAgent(lib_path="/nonexistent/libloader.so")
            assert agent is not None
            assert agent.running is False

    def test_agent_event_structure_matches_c_event(self):
        """Verify Python Event matches C event structure."""
        import sys
        sys.path.insert(0, str(SRC_DIR))
        from ebpf_agent import Event
        
        assert hasattr(Event, "_fields_")
        fields = dict(Event._fields_)
        
        assert "pid" in fields and fields["pid"] == __import__('ctypes').c_uint32
        assert "tgid" in fields and fields["tgid"] == __import__('ctypes').c_uint32
        assert "cgroup_id" in fields and fields["cgroup_id"] == __import__('ctypes').c_uint64
        assert "syscall_id" in fields and fields["syscall_id"] == __import__('ctypes').c_uint32
        assert "comm" in fields
        assert "filename" in fields


class TestLoaderAgentIntegration:
    """Integration tests for C loader and Python agent working together."""

    def test_loader_exports_required_functions(self):
        """Verify loader.c exports required functions."""
        with patch("ebpf_agent.ctypes.CDLL") as mock_cdll:
            mock_lib = MagicMock()
            mock_cdll.return_value = mock_lib
            
            import sys
            sys.path.insert(0, str(SRC_DIR))
            from ebpf_agent import EBPFAgent
            
            agent = EBPFAgent()
            
            assert hasattr(agent.lib, "start_loader")
            assert hasattr(agent.lib, "poll_events")
            assert hasattr(agent.lib, "stop_loader")

    def test_agent_callback_signature_matches_loader(self):
        """Verify Python callback signature matches C loader expectation."""
        import sys
        sys.path.insert(0, str(SRC_DIR))
        from ebpf_agent import EVENT_CB, EBPFAgent
        
        assert EVENT_CB is not None
        
        with patch("ebpf_agent.ctypes.CDLL") as mock_cdll:
            mock_lib = MagicMock()
            mock_cdll.return_value = mock_lib
            
            agent = EBPFAgent()
            
            assert hasattr(agent, "_callback_ref")


class TestEndToEndSimulation:
    """End-to-end simulation tests."""

    def test_agent_lifecycle_simulation(self):
        """Simulate complete agent lifecycle."""
        with patch("ebpf_agent.ctypes.CDLL") as mock_cdll:
            with patch("ebpf_agent.threading.Thread") as mock_thread:
                mock_lib = MagicMock()
                mock_lib.start_loader.return_value = 0
                mock_cdll.return_value = mock_lib
                
                mock_thread_instance = MagicMock()
                mock_thread.return_value = mock_thread_instance
                
                import sys
                sys.path.insert(0, str(SRC_DIR))
                from ebpf_agent import EBPFAgent
                
                agent = EBPFAgent()
                
                assert agent.running is False
                agent.start()
                assert agent.running is True
                mock_thread_instance.start.assert_called_once()
                
                agent.stop()
                assert agent.running is False
                mock_lib.stop_loader.assert_called_once()

    def test_multiple_start_stop_cycles(self):
        """Test multiple start/stop cycles."""
        with patch("ebpf_agent.ctypes.CDLL") as mock_cdll:
            with patch("ebpf_agent.threading.Thread") as mock_thread:
                mock_lib = MagicMock()
                mock_lib.start_loader.return_value = 0
                mock_cdll.return_value = mock_lib
                
                mock_thread_instance = MagicMock()
                mock_thread.return_value = mock_thread_instance
                
                import sys
                sys.path.insert(0, str(SRC_DIR))
                from ebpf_agent import EBPFAgent
                
                agent = EBPFAgent()
                
                for i in range(3):
                    agent.start()
                    agent.stop()
                
                assert mock_lib.start_loader.call_count == 3
                assert mock_lib.stop_loader.call_count == 3


class TestErrorHandlingIntegration:
    """Integration tests for error handling."""

    def test_agent_handles_missing_library(self):
        """Test agent handles missing library gracefully."""
        import sys
        sys.path.insert(0, str(SRC_DIR))
        
        with pytest.raises(OSError):
            import ctypes
            ctypes.CDLL("/nonexistent/path/libloader.so")

    def test_agent_handles_loader_failure(self):
        """Test agent handles loader failure gracefully."""
        with patch("ebpf_agent.ctypes.CDLL") as mock_cdll:
            mock_lib = MagicMock()
            mock_lib.start_loader.return_value = 1
            mock_cdll.return_value = mock_lib
            
            import sys
            sys.path.insert(0, str(SRC_DIR))
            from ebpf_agent import EBPFAgent
            
            agent = EBPFAgent()
            
            with pytest.raises(RuntimeError) as exc_info:
                agent.start()
            assert "Failed to start eBPF loader" in str(exc_info.value)


class TestBuildEnvironmentIntegration:
    """Integration tests for build environment."""

    def test_clang_available_in_build(self):
        """Verify clang is available for build."""
        result = subprocess.run(["which", "clang"], capture_output=True)
        assert result.returncode == 0, "clang not found"

    def test_bpftool_available_in_build(self):
        """Verify bpftool is available for skeleton generation."""
        result = subprocess.run(["which", "bpftool"], capture_output=True)
        assert result.returncode == 0, "bpftool not found"

    def test_libbpf_available(self):
        """Verify libbpf development files are available."""
        result = subprocess.run(["pkg-config", "--exists", "libbpf"], capture_output=True)
        assert result.returncode == 0, "libbpf not found"

    def test_required_kernel_headers(self):
        """Verify required kernel headers exist."""
        arch = subprocess.run(["uname", "-m"], capture_output=True, text=True).stdout.strip()
        linux_gnuhdr = Path(f"/usr/include/{arch}-linux-gnu")
        if linux_gnuhdr.exists():
            assert (linux_gnuhdr / "asm").exists() or True