import ctypes
import os
import queue
import threading
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path
import pytest

ROOT_DIR = Path(__file__).parent.parent.parent; EBPF_AGENT_FILE = ROOT_DIR / "drivers" / "ebpf" / "bridge.py"


class TestEBPFAggentModule:
    """Tests for ebpf_agent.py module structure."""

    def test_ebpf_agent_file_exists(self):
        """Verify ebpf_agent.py exists."""
        assert EBPF_AGENT_FILE.exists(), "ebpf_agent.py not found"

    def test_event_class_defined(self):
        """Verify Event class is defined."""
        import sys
        sys.path.insert(0, str(EBPF_AGENT_FILE.parent))
        from drivers.ebpf.bridge import Event
        assert Event is not None

    def test_event_class_has_required_fields(self):
        """Verify Event class has all required fields."""
        import sys
        sys.path.insert(0, str(EBPF_AGENT_FILE.parent))
        from drivers.ebpf.bridge import Event
        
        field_names = [name for name, _ in Event._fields_]
        required_fields = ["pid", "tgid", "cgroup_id", "syscall_id", "comm", "filename"]
        for field in required_fields:
            assert field in field_names, f"Event missing field: {field}"

    def test_event_field_types(self):
        """Verify Event class has correct field types."""
        import sys
        sys.path.insert(0, str(EBPF_AGENT_FILE.parent))
        from drivers.ebpf.bridge import Event
        
        field_dict = dict(Event._fields_)
        assert field_dict["pid"] == ctypes.c_uint32
        assert field_dict["tgid"] == ctypes.c_uint32
        assert field_dict["cgroup_id"] == ctypes.c_uint64
        assert field_dict["syscall_id"] == ctypes.c_uint32

    def test_event_comm_array_size(self):
        """Verify comm array is 16 bytes."""
        import sys
        sys.path.insert(0, str(EBPF_AGENT_FILE.parent))
        from drivers.ebpf.bridge import Event
        
        field_dict = dict(Event._fields_)
        assert field_dict["comm"] == ctypes.c_char * 16

    def test_event_filename_array_size(self):
        """Verify filename array is 256 bytes."""
        import sys
        sys.path.insert(0, str(EBPF_AGENT_FILE.parent))
        from drivers.ebpf.bridge import Event
        
        field_dict = dict(Event._fields_)
        assert field_dict["filename"] == ctypes.c_char * 256

    def test_event_cb_type_defined(self):
        """Verify EVENT_CB callback type is defined."""
        import sys
        sys.path.insert(0, str(EBPF_AGENT_FILE.parent))
        from drivers.ebpf.bridge import EVENT_CB
        assert EVENT_CB is not None

    def test_ebpf_agent_class_defined(self):
        """Verify EBPFAgent class is defined."""
        import sys
        sys.path.insert(0, str(EBPF_AGENT_FILE.parent))
        from drivers.ebpf.bridge import EBPFAgent
        assert EBPFAgent is not None


class TestEBPFAggentInit:
    """Tests for EBPFAgent initialization."""

    @pytest.fixture
    def mock_cdll(self):
        """Mock ctypes.CDLL."""
        with patch("drivers.ebpf.bridge.ctypes.CDLL") as mock:
            mock_lib = MagicMock()
            mock.return_value = mock_lib
            yield mock_lib

    def test_init_loads_library(self):
        """Verify __init__ loads the shared library."""
        with patch("drivers.ebpf.bridge.ctypes.CDLL") as mock_cdll:
            mock_lib = MagicMock()
            mock_cdll.return_value = mock_lib
            
            import sys
            sys.path.insert(0, str(EBPF_AGENT_FILE.parent))
            from drivers.ebpf.bridge import EBPFAgent
            
            agent = EBPFAgent(lib_path="/fake/path/libloader.so")
            mock_cdll.assert_called_once()

    def test_init_sets_argtypes_for_start_loader(self):
        """Verify start_loader argtypes are set."""
        with patch("drivers.ebpf.bridge.ctypes.CDLL") as mock_cdll:
            mock_lib = MagicMock()
            mock_cdll.return_value = mock_lib
            
            import sys
            sys.path.insert(0, str(EBPF_AGENT_FILE.parent))
            from drivers.ebpf.bridge import EBPFAgent, EVENT_CB
            
            agent = EBPFAgent()
            assert mock_lib.start_loader.argtypes is not None

    def test_init_sets_restype_for_start_loader(self):
        """Verify start_loader restype is set to int."""
        with patch("drivers.ebpf.bridge.ctypes.CDLL") as mock_cdll:
            mock_lib = MagicMock()
            mock_cdll.return_value = mock_lib
            
            import sys
            sys.path.insert(0, str(EBPF_AGENT_FILE.parent))
            from drivers.ebpf.bridge import EBPFAgent
            
            agent = EBPFAgent()
            assert mock_lib.start_loader.restype == ctypes.c_int

    def test_init_sets_argtypes_for_poll_events(self):
        """Verify poll_events argtypes are set."""
        with patch("drivers.ebpf.bridge.ctypes.CDLL") as mock_cdll:
            mock_lib = MagicMock()
            mock_cdll.return_value = mock_lib
            
            import sys
            sys.path.insert(0, str(EBPF_AGENT_FILE.parent))
            from drivers.ebpf.bridge import EBPFAgent
            
            agent = EBPFAgent()
            assert mock_lib.poll_events.argtypes is not None

    def test_init_creates_event_queue(self):
        """Verify __init__ creates an event queue."""
        with patch("drivers.ebpf.bridge.ctypes.CDLL") as mock_cdll:
            mock_lib = MagicMock()
            mock_cdll.return_value = mock_lib
            
            import sys
            sys.path.insert(0, str(EBPF_AGENT_FILE.parent))
            from drivers.ebpf.bridge import EBPFAgent
            
            agent = EBPFAgent()
            assert hasattr(agent, "event_queue")
            assert isinstance(agent.event_queue, queue.Queue)

    def test_init_sets_running_false(self):
        """Verify __init__ sets running to False."""
        with patch("drivers.ebpf.bridge.ctypes.CDLL") as mock_cdll:
            mock_lib = MagicMock()
            mock_cdll.return_value = mock_lib
            
            import sys
            sys.path.insert(0, str(EBPF_AGENT_FILE.parent))
            from drivers.ebpf.bridge import EBPFAgent
            
            agent = EBPFAgent()
            assert agent.running is False

    def test_init_sets_thread_none(self):
        """Verify __init__ sets thread to None."""
        with patch("drivers.ebpf.bridge.ctypes.CDLL") as mock_cdll:
            mock_lib = MagicMock()
            mock_cdll.return_value = mock_lib
            
            import sys
            sys.path.insert(0, str(EBPF_AGENT_FILE.parent))
            from drivers.ebpf.bridge import EBPFAgent
            
            agent = EBPFAgent()
            assert agent.thread is None


class TestEBPFAggentStart:
    """Tests for EBPFAgent.start() method."""

    def test_start_calls_start_loader(self):
        """Verify start() calls start_loader from library."""
        with patch("drivers.ebpf.bridge.ctypes.CDLL") as mock_cdll:
            mock_lib = MagicMock()
            mock_lib.start_loader.return_value = 0
            mock_cdll.return_value = mock_lib
            
            import sys
            sys.path.insert(0, str(EBPF_AGENT_FILE.parent))
            from drivers.ebpf.bridge import EBPFAgent
            
            agent = EBPFAgent()
            agent.start()
            mock_lib.start_loader.assert_called_once()

    def test_start_raises_on_loader_error(self):
        """Verify start() raises RuntimeError when loader fails."""
        with patch("drivers.ebpf.bridge.ctypes.CDLL") as mock_cdll:
            mock_lib = MagicMock()
            mock_lib.start_loader.return_value = 1
            mock_cdll.return_value = mock_lib
            
            import sys
            sys.path.insert(0, str(EBPF_AGENT_FILE.parent))
            from drivers.ebpf.bridge import EBPFAgent
            
            agent = EBPFAgent()
            with pytest.raises(RuntimeError) as exc_info:
                agent.start()
            assert "Failed to start eBPF loader" in str(exc_info.value)

    def test_start_sets_running_true(self):
        """Verify start() sets running to True."""
        with patch("drivers.ebpf.bridge.ctypes.CDLL") as mock_cdll:
            mock_lib = MagicMock()
            mock_lib.start_loader.return_value = 0
            mock_cdll.return_value = mock_lib
            
            import sys
            sys.path.insert(0, str(EBPF_AGENT_FILE.parent))
            from drivers.ebpf.bridge import EBPFAgent
            
            agent = EBPFAgent()
            agent.start()
            assert agent.running is True

    def test_start_creates_thread(self):
        """Verify start() creates a thread."""
        with patch("drivers.ebpf.bridge.ctypes.CDLL") as mock_cdll:
            with patch("drivers.ebpf.bridge.threading.Thread") as mock_thread:
                mock_lib = MagicMock()
                mock_lib.start_loader.return_value = 0
                mock_cdll.return_value = mock_lib
                
                import sys
                sys.path.insert(0, str(EBPF_AGENT_FILE.parent))
                from drivers.ebpf.bridge import EBPFAgent
                
                agent = EBPFAgent()
                agent.start()
                mock_thread.assert_called_once()


class TestEBPFAggentStop:
    """Tests for EBPFAgent.stop() method."""

    def test_stop_sets_running_false(self):
        """Verify stop() sets running to False."""
        with patch("drivers.ebpf.bridge.ctypes.CDLL") as mock_cdll:
            mock_lib = MagicMock()
            mock_lib.start_loader.return_value = 0
            mock_cdll.return_value = mock_lib
            
            import sys
            sys.path.insert(0, str(EBPF_AGENT_FILE.parent))
            from drivers.ebpf.bridge import EBPFAgent
            
            agent = EBPFAgent()
            agent.running = True
            agent.thread = MagicMock()
            agent.stop()
            assert agent.running is False

    def test_stop_calls_stop_loader(self):
        """Verify stop() calls stop_loader from library."""
        with patch("drivers.ebpf.bridge.ctypes.CDLL") as mock_cdll:
            mock_lib = MagicMock()
            mock_cdll.return_value = mock_lib
            
            import sys
            sys.path.insert(0, str(EBPF_AGENT_FILE.parent))
            from drivers.ebpf.bridge import EBPFAgent
            
            agent = EBPFAgent()
            agent.thread = MagicMock()
            agent.stop()
            mock_lib.stop_loader.assert_called_once()

    def test_stop_joins_thread_if_exists(self):
        """Verify stop() joins thread if it exists."""
        with patch("drivers.ebpf.bridge.ctypes.CDLL") as mock_cdll:
            mock_lib = MagicMock()
            mock_cdll.return_value = mock_lib
            
            import sys
            sys.path.insert(0, str(EBPF_AGENT_FILE.parent))
            from drivers.ebpf.bridge import EBPFAgent
            
            agent = EBPFAgent()
            mock_thread = MagicMock()
            agent.thread = mock_thread
            agent.stop()
            mock_thread.join.assert_called_once()


class TestEBPFAggentGetEvent:
    """Tests for EBPFAgent.get_event() method."""

    def test_get_event_returns_event(self):
        """Verify get_event returns event from queue."""
        with patch("drivers.ebpf.bridge.ctypes.CDLL") as mock_cdll:
            mock_lib = MagicMock()
            mock_cdll.return_value = mock_lib
            
            import sys
            sys.path.insert(0, str(EBPF_AGENT_FILE.parent))
            from drivers.ebpf.bridge import EBPFAgent
            
            agent = EBPFAgent()
            test_event = {"pid": 123, "comm": "test"}
            agent.event_queue.put(test_event)
            
            result = agent.get_event(block=False)
            assert result == test_event

    def test_get_event_returns_none_on_empty(self):
        """Verify get_event returns None when queue is empty."""
        with patch("drivers.ebpf.bridge.ctypes.CDLL") as mock_cdll:
            mock_lib = MagicMock()
            mock_cdll.return_value = mock_lib
            
            import sys
            sys.path.insert(0, str(EBPF_AGENT_FILE.parent))
            from drivers.ebpf.bridge import EBPFAgent
            
            agent = EBPFAgent()
            result = agent.get_event(block=False)
            assert result is None


class TestEBPFAggentEventHandler:
    """Tests for EBPFAgent._event_handler() method."""

    def test_event_handler_puts_to_queue(self):
        """Verify _event_handler puts event to queue."""
        with patch("drivers.ebpf.bridge.ctypes.CDLL") as mock_cdll:
            mock_lib = MagicMock()
            mock_cdll.return_value = mock_lib
            
            import sys
            sys.path.insert(0, str(EBPF_AGENT_FILE.parent))
            from drivers.ebpf.bridge import EBPFAgent
            
            agent = EBPFAgent()
            
            mock_event = MagicMock()
            mock_event.pid = 123
            mock_event.tgid = 456
            mock_event.cgroup_id = 789
            mock_event.syscall_id = 257
            mock_event.comm = b"testproc"
            mock_event.filename = b"/tmp/test"
            
            mock_ptr = MagicMock()
            mock_ptr.contents = mock_event
            
            agent._event_handler(None, mock_ptr, 100)
            
            assert not agent.event_queue.empty()
            event = agent.event_queue.get_nowait()
            assert event["pid"] == 123
            assert event["tgid"] == 456

    def test_event_handler_decodes_comm_utf8(self):
        """Verify _event_handler decodes comm as UTF-8."""
        with patch("drivers.ebpf.bridge.ctypes.CDLL") as mock_cdll:
            mock_lib = MagicMock()
            mock_cdll.return_value = mock_lib
            
            import sys
            sys.path.insert(0, str(EBPF_AGENT_FILE.parent))
            from drivers.ebpf.bridge import EBPFAgent
            
            agent = EBPFAgent()
            
            mock_event = MagicMock()
            mock_event.pid = 123
            mock_event.tgid = 456
            mock_event.cgroup_id = 789
            mock_event.syscall_id = 257
            mock_event.comm = b"test"
            mock_event.filename = b"/tmp/test"
            
            mock_ptr = MagicMock()
            mock_ptr.contents = mock_event
            
            agent._event_handler(None, mock_ptr, 100)
            
            event = agent.event_queue.get_nowait()
            assert isinstance(event["comm"], str)


class TestEBPFAggentPollLoop:
    """Tests for EBPFAgent._poll_loop() method."""

    @pytest.mark.skip(reason="time module imported locally in __main__, difficult to mock properly")
    def test_poll_loop_calls_poll_events(self):
        """Verify _poll_loop calls poll_events."""
        pass


class TestEBPFAggentEdgeCases:
    """Tests for edge cases in EBPFAgent."""

    def test_get_event_with_timeout(self):
        """Verify get_event works with timeout parameter."""
        with patch("drivers.ebpf.bridge.ctypes.CDLL") as mock_cdll:
            mock_lib = MagicMock()
            mock_cdll.return_value = mock_lib
            
            import sys
            sys.path.insert(0, str(EBPF_AGENT_FILE.parent))
            from drivers.ebpf.bridge import EBPFAgent
            
            agent = EBPFAgent()
            result = agent.get_event(block=True, timeout=0.1)
            assert result is None

    def test_stop_with_no_thread(self):
        """Verify stop() handles None thread gracefully."""
        with patch("drivers.ebpf.bridge.ctypes.CDLL") as mock_cdll:
            mock_lib = MagicMock()
            mock_cdll.return_value = mock_lib
            
            import sys
            sys.path.insert(0, str(EBPF_AGENT_FILE.parent))
            from drivers.ebpf.bridge import EBPFAgent
            
            agent = EBPFAgent()
            agent.thread = None
            agent.stop()
            mock_lib.stop_loader.assert_called_once()