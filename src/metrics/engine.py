import numpy as np
import logging
from typing import Dict, List, Optional, Tuple
from collections import deque

logger = logging.getLogger(__name__)

class MetricsEngine:
    """
    Implements the mathematical model M(t) from Section 2.1.
    Calculates EWMA (Exponentially Weighted Moving Average) for system metrics
    and maintains n-gram profiles for syscall sequences.
    """
    
    def __init__(self, alpha: float = 0.3, n_gram_size: int = 3):
        self.alpha = alpha  # Smoothing factor for EWMA
        self.n_gram_size = n_gram_size
        
        # Structure: {pid: {"metrics": array, "mu": array, "sigma": array, "ngram_tree": dict}}
        self.profiles: Dict[int, Dict] = {}

    def update_scalar_metrics(self, pid: int, current_vector: np.ndarray):
        """
        Updates EWMA for a process.
        z_i = (m_i - mu_i) / sigma_i
        """
        if pid not in self.profiles:
            self.profiles[pid] = {
                "mu": current_vector.astype(float),
                "sigma": np.ones_like(current_vector, dtype=float),
                "history": deque(maxlen=100),
                "ngram_buffer": deque(maxlen=self.n_gram_size),
                "ngram_counts": {}
            }
            return

        prof = self.profiles[pid]
        
        # EWMA Update: mu = alpha * current + (1 - alpha) * mu
        old_mu = prof["mu"]
        new_mu = self.alpha * current_vector + (1 - self.alpha) * old_mu
        
        # Incremental variance/sigma calculation (Simplified)
        delta = current_vector - old_mu
        prof["sigma"] = np.sqrt((1 - self.alpha) * (prof["sigma"]**2 + self.alpha * delta**2))
        prof["mu"] = new_mu
        
        prof["history"].append(current_vector)

    def update_ngram(self, pid: int, syscall_id: int):
        """
        Updates the n-gram frequency distribution for the process.
        """
        if pid not in self.profiles:
            # Initialize if not exists (should normally be handled by scalar update)
            self.update_scalar_metrics(pid, np.zeros(5)) 
            
        prof = self.profiles[pid]
        buf = prof["ngram_buffer"]
        buf.append(syscall_id)
        
        if len(buf) == self.n_gram_size:
            ngram = tuple(buf)
            prof["ngram_counts"][ngram] = prof["ngram_counts"].get(ngram, 0) + 1

    def get_z_scores(self, pid: int, current_vector: np.ndarray) -> np.ndarray:
        """
        Computes Z-scores for the current observation against the stored profile.
        """
        if pid not in self.profiles:
            return np.zeros_like(current_vector)
            
        prof = self.profiles[pid]
        # Avoid division by zero
        safe_sigma = np.where(prof["sigma"] == 0, 1e-6, prof["sigma"])
        return (current_vector - prof["mu"]) / safe_sigma

    def get_ngram_anomaly_score(self, pid: int, sequence: Tuple[int, ...]) -> float:
        """
        Returns a score representing how 'new' or 'rare' a sequence is.
        Higher is more anomalous.
        """
        if pid not in self.profiles:
            return 1.0
            
        counts = self.profiles[pid]["ngram_counts"]
        total = sum(counts.values())
        if total == 0:
            return 1.0
            
        freq = counts.get(sequence, 0) / total
        return 1.0 - freq # Inverse frequency as anomaly indicator
