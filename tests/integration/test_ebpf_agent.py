"""Tests for drivers/ebpf/bridge.py.

The Python bridge wraps the C loader (``libloader.so``) via ctypes.
Tests here exercise the public surface without loading the real
shared library by stubbing the lib path and patching ``ctypes.CDLL``
where needed.
"""

import ctypes
import queue
import threading
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from drivers.ebpf.bridge import (
    EBPFAgent,
    Event,
    event_to_dict,
    OP_OPEN,
    OP_CLOSE,
    OP_READ,
    OP_WRITE,
    FD_TYPE_FILE,
    FD_TYPE_SOCKET,
)


ROOT_DIR = Path(__file__).parent.parent.parent
FAKE_LIB = "/nonexistent/libloader.so"


# ── Event ctypes layout ──────────────────────────────────────────────


class TestEventLayout:
    """Tests for the ``Event`` ctypes Structure."""

    def test_event_class_defined(self):
        assert Event is not None

    def test_event_class_has_required_fields(self):
        field_names = [name for name, _ in Event._fields_]
        required = ["pid", "tgid", "cgroup_id", "op_type", "fd",
                    "fd_type", "bytes", "timestamp_ns", "comm", "filename"]
        for f in required:
            assert f in field_names, f"Event missing field: {f}"

    def test_event_field_types(self):
        fields = dict(Event._fields_)
        assert fields["pid"] == ctypes.c_uint32
        assert fields["tgid"] == ctypes.c_uint32
        assert fields["cgroup_id"] == ctypes.c_uint64
        assert fields["op_type"] == ctypes.c_uint32
        assert fields["fd"] == ctypes.c_uint32
        assert fields["fd_type"] == ctypes.c_uint32
        assert fields["bytes"] == ctypes.c_uint64

    def test_event_comm_array_size(self):
        fields = dict(Event._fields_)
        assert fields["comm"] == ctypes.c_char * 16

    def test_event_filename_array_size(self):
        """filename was shrunk to 128 bytes (commit b8f7dcf) to fit
        the eBPF program stack budget."""
        fields = dict(Event._fields_)
        assert fields["filename"] == ctypes.c_char * 128


class TestEventToDict:
    """Tests for the ``event_to_dict`` serializer."""

    def _make_event(self, **overrides):
        e = Event()
        e.pid = overrides.get("pid", 100)
        e.tgid = overrides.get("tgid", 100)
        e.cgroup_id = overrides.get("cgroup_id", 0)
        e.op_type = overrides.get("op_type", OP_OPEN)
        e.fd = overrides.get("fd", 3)
        e.fd_type = overrides.get("fd_type", FD_TYPE_FILE)
        e.bytes = overrides.get("bytes", 0)
        e.timestamp_ns = overrides.get("timestamp_ns", 0)
        e.comm = overrides.get("comm", b"testproc")
        e.filename = overrides.get("filename", b"/tmp/x")
        return e

    def test_returns_dict_with_all_fields(self):
        d = event_to_dict(self._make_event())
        for key in ("pid", "tgid", "cgroup_id", "op_type", "op_name",
                    "fd", "fd_type", "fd_type_name", "bytes",
                    "timestamp_ns", "comm", "filename"):
            assert key in d

    def test_decodes_comm_as_utf8_string(self):
        d = event_to_dict(self._make_event(comm=b"nginx"))
        assert isinstance(d["comm"], str)
        assert d["comm"] == "nginx"

    def test_maps_op_type_to_op_name(self):
        for op, name in [(OP_OPEN, "open"), (OP_CLOSE, "close"),
                         (OP_READ, "read"), (OP_WRITE, "write")]:
            d = event_to_dict(self._make_event(op_type=op))
            assert d["op_name"] == name

    def test_maps_fd_type_to_name(self):
        d = event_to_dict(self._make_event(fd_type=FD_TYPE_SOCKET))
        assert d["fd_type_name"] == "socket"


# ── EBPFAgent ────────────────────────────────────────────────────────


class TestEBPFAgentInit:
    """Init does not touch the shared library — the .so is loaded
    lazily inside ``start()`` so unit tests can construct an agent
    without any real eBPF dependency."""

    def test_init_accepts_lib_path(self):
        agent = EBPFAgent(lib_path=FAKE_LIB)
        assert agent.lib_path == Path(FAKE_LIB)

    def test_init_does_not_load_library(self):
        agent = EBPFAgent(lib_path=FAKE_LIB)
        assert agent.lib is None

    def test_init_creates_event_queue(self):
        agent = EBPFAgent(lib_path=FAKE_LIB)
        assert isinstance(agent._event_queue, queue.Queue)

    def test_init_sets_polling_false(self):
        agent = EBPFAgent(lib_path=FAKE_LIB)
        assert agent._polling is False

    def test_init_sets_poll_thread_none(self):
        agent = EBPFAgent(lib_path=FAKE_LIB)
        assert agent._poll_thread is None


class TestEBPFAgentStart:

    def test_start_raises_if_library_missing(self):
        agent = EBPFAgent(lib_path="/definitely/not/here.so")
        with pytest.raises(FileNotFoundError):
            agent.start()

    def test_start_calls_start_loader(self, tmp_path):
        # Create a placeholder file so the existence check passes;
        # CDLL is patched so the file is never actually dlopened.
        fake_so = tmp_path / "libloader.so"
        fake_so.write_bytes(b"")
        agent = EBPFAgent(lib_path=str(fake_so))

        with patch("drivers.ebpf.bridge.ctypes.CDLL") as mock_cdll:
            mock_lib = MagicMock()
            mock_lib.start_loader.return_value = 0
            mock_cdll.return_value = mock_lib
            agent.start()
            mock_lib.start_loader.assert_called_once()
        agent.stop()

    def test_start_raises_on_loader_error(self, tmp_path):
        fake_so = tmp_path / "libloader.so"
        fake_so.write_bytes(b"")
        agent = EBPFAgent(lib_path=str(fake_so))

        with patch("drivers.ebpf.bridge.ctypes.CDLL") as mock_cdll:
            mock_lib = MagicMock()
            mock_lib.start_loader.return_value = 1
            mock_cdll.return_value = mock_lib
            with pytest.raises(RuntimeError) as exc:
                agent.start()
            assert "Failed to start eBPF loader" in str(exc.value)

    def test_start_sets_polling_true(self, tmp_path):
        fake_so = tmp_path / "libloader.so"
        fake_so.write_bytes(b"")
        agent = EBPFAgent(lib_path=str(fake_so))

        with patch("drivers.ebpf.bridge.ctypes.CDLL") as mock_cdll:
            mock_lib = MagicMock()
            mock_lib.start_loader.return_value = 0
            mock_cdll.return_value = mock_lib
            agent.start()
            assert agent._polling is True
        agent.stop()


class TestEBPFAgentStop:

    def test_stop_clears_polling(self, tmp_path):
        fake_so = tmp_path / "libloader.so"
        fake_so.write_bytes(b"")
        agent = EBPFAgent(lib_path=str(fake_so))

        with patch("drivers.ebpf.bridge.ctypes.CDLL") as mock_cdll:
            mock_lib = MagicMock()
            mock_lib.start_loader.return_value = 0
            mock_cdll.return_value = mock_lib
            agent.start()
            agent.stop()
            assert agent._polling is False
            mock_lib.stop_loader.assert_called_once()

    def test_stop_without_start_is_safe(self):
        agent = EBPFAgent(lib_path=FAKE_LIB)
        agent.stop()  # should not raise


class TestEBPFAgentGetEvent:

    def test_get_event_returns_none_on_empty(self):
        agent = EBPFAgent(lib_path=FAKE_LIB)
        assert agent.get_event(timeout=0.05) is None

    def test_get_event_drains_queue(self):
        agent = EBPFAgent(lib_path=FAKE_LIB)
        e = Event()
        e.pid = 4242
        e.comm = b"alpha"
        e.filename = b"/etc/x"
        agent._event_queue.put(e)
        result = agent.get_event(timeout=0.05)
        assert result is not None
        assert result["pid"] == 4242
        assert result["comm"] == "alpha"


class TestEBPFAgentCallback:
    """The C library invokes ``_c_callback(ctx, data, size)``; data is
    a void* pointing at an ``Event``. The callback copies the event
    into the queue without blocking."""

    def test_callback_drops_undersized_events(self):
        agent = EBPFAgent(lib_path=FAKE_LIB)
        # Pretend the buffer is smaller than an Event; should be ignored.
        agent._c_callback(None, ctypes.c_void_p(0), 4)
        assert agent._event_queue.empty()

    def test_callback_pushes_valid_event(self):
        agent = EBPFAgent(lib_path=FAKE_LIB)
        e = Event()
        e.pid = 777
        ptr = ctypes.cast(ctypes.pointer(e), ctypes.c_void_p)
        agent._c_callback(None, ptr, ctypes.sizeof(Event))
        assert not agent._event_queue.empty()
        got = agent._event_queue.get_nowait()
        assert got.pid == 777
