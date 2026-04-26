import ctypes
import os
import threading
import queue
from dataclasses import dataclass

# Define the event structure matching tracer.bpf.c
class Event(ctypes.Structure):
    _fields_ = [
        ("pid", ctypes.c_uint32),
        ("tgid", ctypes.c_uint32),
        ("cgroup_id", ctypes.c_uint64),
        ("syscall_id", ctypes.c_uint32),
        ("comm", ctypes.c_char * 16),
        ("filename", ctypes.c_char * 256),
    ]

# Callback type for the C loader
EVENT_CB = ctypes.CFUNCTYPE(None, ctypes.c_void_p, ctypes.POINTER(Event), ctypes.c_size_t)

class EBPFAgent:
    def __init__(self, lib_path="./ebpf/libloader.so"):
        self.lib = ctypes.CDLL(os.path.abspath(lib_path))
        self.event_queue = queue.Queue()
        
        self.lib.start_loader.argtypes = [EVENT_CB]
        self.lib.start_loader.restype = ctypes.c_int
        
        self.lib.poll_events.argtypes = [ctypes.c_int]
        self.lib.poll_events.restype = ctypes.c_int
        
        self.lib.stop_loader.argtypes = []
        self.lib.stop_loader.restype = None
        
        self._callback_ref = EVENT_CB(self._event_handler)
        self.running = False
        self.thread = None

    def _event_handler(self, ctx, event_ptr, size):
        event = event_ptr.contents
        # Copy data out of the BPF ring buffer to the Python queue
        self.event_queue.put({
            "pid": event.pid,
            "tgid": event.tgid,
            "cgroup_id": event.cgroup_id,
            "syscall_id": event.syscall_id,
            "comm": event.comm.decode('utf-8', 'replace'),
            "filename": event.filename.decode('utf-8', 'replace')
        })

    def start(self):
        err = self.lib.start_loader(self._callback_ref)
        if err != 0:
            raise RuntimeError(f"Failed to start eBPF loader: {err}")
        
        self.running = True
        self.thread = threading.Thread(target=self._poll_loop, daemon=True)
        self.thread.start()

    def _poll_loop(self):
        while self.running:
            self.lib.poll_events(100) # 100ms timeout

    def stop(self):
        self.running = False
        if self.thread:
            self.thread.join()
        self.lib.stop_loader()

    def get_event(self, block=True, timeout=None):
        try:
            return self.event_queue.get(block=block, timeout=timeout)
        except queue.Empty:
            return None

if __name__ == "__main__":
    # Basic test if run directly
    import time
    agent = EBPFAgent()
    print("Starting agent... (requires root/CAP_BPF)")
    try:
        agent.start()
        print("Monitoring... Press Ctrl+C to stop")
        while True:
            event = agent.get_event(timeout=1)
            if event:
                print(f"Event: {event}")
    except KeyboardInterrupt:
        pass
    finally:
        agent.stop()
