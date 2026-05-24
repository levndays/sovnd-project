import os
import subprocess
import pytest
from pathlib import Path

ROOT_DIR = Path(__file__).parent.parent.parent
EBPF_DIR = ROOT_DIR / "drivers" / "ebpf"


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
        required_src = ["tracer.bpf.c", "filter.bpf.c", "fd_tracker.bpf.c"]
        required_inc = ["maps.bpf.h", "vmlinux.h"]
        
        for filename in required_src:
            filepath = EBPF_DIR / "src" / filename
            assert filepath.exists(), f"Required file src/{filename} not found"
            
        for filename in required_inc:
            filepath = EBPF_DIR / "include" / filename
            assert filepath.exists(), f"Required file include/{filename} not found"

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

    def test_loader_c_exists(self):
        """Verify loader.c source file exists."""
        loader_c = EBPF_DIR / "loader" / "loader.c"
        assert loader_c.exists(), "loader.c not found"

    def test_compile_libloader_so(self):
        """Test that libloader.so can be compiled."""
        result = subprocess.run(
            ["make", "all"],
            cwd=EBPF_DIR,
            capture_output=True,
            text=True
        )
        assert result.returncode == 0, f"Compilation failed: {result.stderr}"
        
        libloader_so = EBPF_DIR / "libloader.so"
        assert libloader_so.exists(), "libloader.so was not created"

    def test_libloader_so_size(self):
        """Test that libloader.so has reasonable size."""
        libloader_so = EBPF_DIR / "libloader.so"
        if not libloader_so.exists():
            subprocess.run(["make", "all"], cwd=EBPF_DIR, check=True)
        
        size = libloader_so.stat().st_size
        assert size > 0, "libloader.so is empty"
        assert size < 10 * 1024 * 1024, "libloader.so is unreasonably large (>10MB)"

    def test_skeleton_header_generated(self):
        """Test that tracer.skel.h is generated."""
        result = subprocess.run(
            ["make", "all"],
            cwd=EBPF_DIR,
            capture_output=True,
            text=True
        )
        assert result.returncode == 0, f"Build failed: {result.stderr}"
        
        skel_h = EBPF_DIR / "tracer.skel.h"
        assert skel_h.exists(), "tracer.skel.h was not generated"

    def test_bpftool_available(self):
        """Test that bpftool is available."""
        result = subprocess.run(
            ["which", "bpftool"],
            capture_output=True
        )
        assert result.returncode == 0, "bpftool not found in PATH"

    def test_libbpf_dev_available(self):
        """Test that libbpf development headers are available."""
        result = subprocess.run(
            ["pkg-config", "--exists", "libbpf"],
            capture_output=True
        )
        assert result.returncode == 0, "libbpf development files not found"
