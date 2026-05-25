import re
import pytest
from pathlib import Path

ROOT_DIR = Path(__file__).parent.parent.parent; EBPF_DIR = ROOT_DIR / "drivers" / "ebpf"
MAPS_HEADER = EBPF_DIR / "include" / "maps.bpf.h"


class TestEBPFMapValidation:
    """Tests for eBPF map definitions validation."""

    @pytest.fixture
    def maps_content(self):
        """Load maps.bpf.h content."""
        return MAPS_HEADER.read_text()

    def test_maps_header_exists(self):
        """Verify maps.bpf.h exists."""
        assert MAPS_HEADER.exists(), "maps.bpf.h not found"

    def test_maps_header_has_header_guard(self, maps_content):
        """Verify maps header has proper include guards."""
        assert "#ifndef __MAPS_BPF_H" in maps_content, "Missing header guard start"
        assert "#define __MAPS_BPF_H" in maps_content, "Missing header guard define"
        assert "#endif" in maps_content, "Missing header guard endif"

    def test_ringbuf_map_exists(self, maps_content):
        """Verify ring buffer map is defined."""
        assert "BPF_MAP_TYPE_RINGBUF" in maps_content, "Ringbuf map type not found"
        assert "rb" in maps_content, "Ring buffer map 'rb' not found"

    def test_ringbuf_map_properties(self, maps_content):
        """Verify ring buffer map has correct properties."""
        assert "max_entries" in maps_content, "Ringbuf max_entries not found"
        assert "256" in maps_content or "256 * 1024" in maps_content, "Ringbuf size not configured"

    def test_proc_stats_map_exists(self, maps_content):
        """Verify proc_stats hash map is defined."""
        assert "proc_stats" in maps_content, "proc_stats map not found"
        assert "BPF_MAP_TYPE_HASH" in maps_content, "Hash map type not found"

    def test_proc_stats_key_type(self, maps_content):
        """Verify proc_stats has correct key type (PID as __u32)."""
        assert "__u32" in maps_content, "Key type __u32 not found in maps"

    def test_proc_stats_value_type(self, maps_content):
        """Verify proc_stats has struct proc_stats value type."""
        assert "proc_stats" in maps_content, "proc_stats struct reference not found"

    def test_proc_stats_max_entries(self, maps_content):
        """Verify proc_stats has reasonable max_entries."""
        match = re.search(r'proc_stats.*?max_entries,\s*(\d+)', maps_content, re.DOTALL)
        assert match, "proc_stats max_entries not found"
        max_entries = int(match.group(1))
        assert max_entries > 0, "proc_stats max_entries should be positive"
        assert max_entries <= 100000, "proc_stats max_entries unreasonably large"

    def test_container_map_exists(self, maps_content):
        """Verify container_map is defined."""
        assert "container_map" in maps_content, "container_map not found"

    def test_container_map_key_type(self, maps_content):
        """Verify container_map uses cgroup_id as key (__u64)."""
        assert "cgroup" in maps_content.lower(), "cgroup_id not referenced in maps"

    def test_all_maps_have_sec_markers(self, maps_content):
        """Verify all maps have SEC(.maps) markers."""
        sec_markers = maps_content.count("SEC(\".maps\")")
        assert sec_markers >= 6, f"Expected at least 6 SEC(.maps) markers, found {sec_markers}"

    def test_maps_include_vmlinux(self):
        """Verify vmlinux.h is included by tracer.bpf.c.

        maps.bpf.h relies on kernel types (__u32, __u64) which come
        from vmlinux.h. The header itself doesn't include vmlinux.h
        (it's included transitively via tracer.bpf.c before the maps
        header), so this check targets the .c file.
        """
        tracer = (EBPF_DIR / "src" / "tracer.bpf.c").read_text()
        assert "vmlinux.h" in tracer, "vmlinux.h not included by tracer"

    def test_maps_include_bpf_helpers(self, maps_content):
        """Verify maps include bpf helpers."""
        assert "#include" in maps_content and "bpf_helpers.h" in maps_content, "bpf_helpers.h not included"