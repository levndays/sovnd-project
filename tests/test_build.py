import os
import subprocess
import pytest
from pathlib import Path

EBPF_DIR = Path(__file__).parent.parent / "ebpf"


class TestBuildCompilation:
    """Tests for eBPF build and compilation."""

    def test_makefile_exists(self):
        """Verify Makefile exists in ebpf directory."""
        makefile = EBPF_DIR / "Makefile"
        assert makefile.exists(), "Makefile not found in ebpf directory"

    def test_makefile_has_targets(self):
        """Verify Makefile has required targets."""
        makefile_content = (EBPF_DIR / "Makefile").read_text()
        assert "all:" in makefile_content, "Makefile missing 'all' target"
        assert "clean:" in makefile_content, "Makefile missing 'clean' target"

    def test_compile_tracer_bpf_o(self):
        """Test that tracer.bpf.o can be compiled."""
        result = subprocess.run(
            ["make", "all"],
            cwd=EBPF_DIR,
            capture_output=True,
            text=True
        )
        assert result.returncode == 0, f"Compilation failed: {result.stderr}"
        
        tracer_o = EBPF_DIR / "tracer.bpf.o"
        assert tracer_o.exists(), "tracer.bpf.o was not created"

    def test_compiled_object_file_size(self):
        """Test that compiled object file has reasonable size."""
        tracer_o = EBPF_DIR / "tracer.bpf.o"
        assert tracer_o.exists(), "tracer.bpf.o not found"
        
        size = tracer_o.stat().st_size
        assert size > 0, "tracer.bpf.o is empty"
        assert size < 1024 * 1024, "tracer.bpf.o is unreasonably large (>1MB)"

    def test_source_files_exist(self):
        """Verify all required source files exist."""
        required_files = [
            "tracer.bpf.c",
            "filter.bpf.c",
            "fd_tracker.bpf.c",
            "maps.bpf.h",
            "vmlinux.h"
        ]
        for filename in required_files:
            filepath = EBPF_DIR / filename
            assert filepath.exists(), f"Required file {filename} not found"

    def test_clang_available(self):
        """Test that clang compiler is available."""
        result = subprocess.run(
            ["which", "clang"],
            capture_output=True
        )
        assert result.returncode == 0, "clang not found in PATH"

    def test_clean_target(self):
        """Test that make clean works without errors."""
        subprocess.run(["make", "all"], cwd=EBPF_DIR, check=True)
        
        result = subprocess.run(
            ["make", "clean"],
            cwd=EBPF_DIR,
            capture_output=True,
            text=True
        )
        assert result.returncode == 0, f"make clean failed: {result.stderr}"