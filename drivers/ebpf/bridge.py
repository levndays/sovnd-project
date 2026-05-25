import ctypes
import logging
import threading
import queue
import time
from pathlib import Path
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)

class Event(ctypes.Structure):
    _fields_ = [
        ("pid",         ctypes.c_uint32),
        ("tgid",        ctypes.c_uint32),
        ("cgroup_id",   ctypes.c_uint64),
        ("op_type",     ctypes.c_uint32),
        ("fd",          ctypes.c_uint32),
        ("fd_type",     ctypes.c_uint32),
        ("bytes",       ctypes.c_uint64),
        ("timestamp_ns",ctypes.c_uint64),
        ("comm",        ctypes.c_char * 16),
        ("filename",    ctypes.c_char * 128),
    ]

OP_OPEN  = 1
OP_CLOSE = 2
OP_READ  = 3
OP_WRITE = 4

FD_TYPE_FILE   = 1
FD_TYPE_SOCKET = 2
FD_TYPE_PIPE   = 3
FD_TYPE_ANON   = 4
FD_TYPE_UNKNOWN = 0

OP_NAMES = {OP_OPEN: "open", OP_CLOSE: "close", OP_READ: "read", OP_WRITE: "write"}
FD_TYPE_NAMES = {
    FD_TYPE_FILE: "file", FD_TYPE_SOCKET: "socket",
    FD_TYPE_PIPE: "pipe", FD_TYPE_ANON: "anon", FD_TYPE_UNKNOWN: "unknown"
}

def event_to_dict(evt: Event) -> Dict[str, Any]:
    return {
        "pid":         evt.pid,
        "tgid":        evt.tgid,
        "cgroup_id":   evt.cgroup_id,
        "op_type":     evt.op_type,
        "op_name":     OP_NAMES.get(evt.op_type, "?"),
        "fd":          evt.fd,
        "fd_type":     evt.fd_type,
        "fd_type_name": FD_TYPE_NAMES.get(evt.fd_type, "?"),
        "bytes":       evt.bytes,
        "timestamp_ns": evt.timestamp_ns,
        "comm":        evt.comm.decode("utf-8", errors="replace").strip("\x00"),
        "filename":    evt.filename.decode("utf-8", errors="replace").strip("\x00"),
    }

class EBPFAgent:
    def __init__(self, lib_path: str):
        self.lib_path = Path(lib_path)
        self.lib = None
        self._event_queue = queue.Queue()
        self._polling = False
        self._poll_thread = None
        self._ctx = None

    def _c_callback(self, ctx, data, size):
        if size < ctypes.sizeof(Event):
            return
        evt = ctypes.cast(data, ctypes.POINTER(Event)).contents
        self._event_queue.put(evt)

    def start(self):
        if not self.lib_path.exists():
            raise FileNotFoundError(f"libloader.so not found at {self.lib_path}")

        CBFUNC = ctypes.CFUNCTYPE(None, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_size_t)
        self._callback = CBFUNC(self._c_callback)

        self.lib = ctypes.CDLL(str(self.lib_path))
        self.lib.start_loader.argtypes = [CBFUNC]
        self.lib.start_loader.restype = ctypes.c_int
        self.lib.poll_events.argtypes = [ctypes.c_int]
        self.lib.poll_events.restype = ctypes.c_int
        self.lib.stop_loader.argtypes = []
        self.lib.stop_loader.restype = None
        self.lib.set_target_cgroup.argtypes = [ctypes.c_ulonglong]
        self.lib.set_target_cgroup.restype = ctypes.c_int

        err = self.lib.start_loader(self._callback)
        if err != 0:
            raise RuntimeError(f"Failed to start eBPF loader (err={err})")

        self._polling = True
        self._poll_thread = threading.Thread(target=self._poll_loop, daemon=True)
        self._poll_thread.start()

    def _poll_loop(self):
        while self._polling:
            try:
                self.lib.poll_events(100)
            except Exception:
                time.sleep(0.1)

    def get_event(self, timeout: float = 1.0) -> Optional[Dict[str, Any]]:
        try:
            evt = self._event_queue.get(timeout=timeout)
            return event_to_dict(evt)
        except queue.Empty:
            return None

    def set_target_cgroup(self, cgroup_id: int) -> int:
        """Narrow in-kernel filtering to a single cgroup.

        Pass the cgroup v2 inode (as returned by
        ``ContainerResolver.find_target_cgroup_inode``) to make the
        eBPF tracer drop events from every other cgroup. Pass 0 to
        disable the filter. Must be called after ``start()``.
        """
        if self.lib is None:
            raise RuntimeError("set_target_cgroup called before start()")
        return self.lib.set_target_cgroup(ctypes.c_ulonglong(cgroup_id))

    def stop(self):
        self._polling = False
        if self._poll_thread:
            self._poll_thread.join(timeout=2.0)
        if self.lib:
            self.lib.stop_loader()
