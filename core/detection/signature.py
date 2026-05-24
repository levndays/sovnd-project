import re
import logging
from typing import List, Dict, Optional, Any

logger = logging.getLogger(__name__)

class SignatureDetector:
    """
    Implements fast signature-based detection (Section 2.2).
    Checks for sensitive file access and known malicious patterns.
    """
    
    def __init__(self):
        # High-priority sensitive paths (IOCs)
        self.critical_paths = [
            re.compile(r'^/etc/shadow$'),
            re.compile(r'^/etc/sudoers$'),
            re.compile(r'^/var/run/docker\.sock$'),
            re.compile(r'^/root/.ssh/.*'),
            re.compile(r'^/proc/kcore$')
        ]
        
        # Suspicious patterns (e.g., shell access from web server)
        self.suspicious_comm = ["bash", "sh", "nc", "ncat", "python", "perl"]

    def analyze_event(self, event: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Quickly scans an event for signature matches.
        """
        filename = event.get("filename") or ""
        comm = event.get("comm") or ""
        
        if not filename:
            return None
        
        # Check for sensitive path access
        for pattern in self.critical_paths:
            if pattern.match(filename):
                return {
                    "type": "SIGNATURE_MATCH",
                    "reason": f"Access to critical file: {filename}",
                    "severity": "critical",
                    "ioc": filename
                }
        
        # Check for suspicious process execution (simplified)
        # In a real impl, we'd check if a non-shell process spawns a shell
        if any(s in comm for s in self.suspicious_comm):
            # This is a heuristic, should be combined with context
            if "/bin/" in filename or "/usr/bin/" in filename:
                return {
                    "type": "HEURISTIC_MATCH",
                    "reason": f"Suspicious process activity: {comm}",
                    "severity": "warning"
                }
                
        return None
