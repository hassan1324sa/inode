import random
import time
from enum import Enum
from typing import Optional, List, Dict, Any
from app.core.execution.errors import TransientError, PermanentError

class ChaosMode(str, Enum):
    NONE = "NONE"
    LATENCY_INJECTION = "LATENCY_INJECTION"
    NETWORK_PARTITION = "NETWORK_PARTITION"
    WORKER_FAILURE = "WORKER_FAILURE"
    ERROR_RATE = "ERROR_RATE"

class ChaosException(TransientError):
    """
    Transient exception injected by ChaosSimulator to test retry and failover resilience.
    """
    pass

class ChaosSimulator:
    """
    Chaos Engineering framework for simulating faults, network partitions, latency, and worker crashes.
    """
    _enabled: bool = False
    _mode: ChaosMode = ChaosMode.NONE
    _error_probability: float = 0.5
    _latency_ms: float = 100.0
    _targeted_nodes: set = set()

    @classmethod
    def enable(
        cls,
        mode: ChaosMode,
        error_probability: float = 0.5,
        latency_ms: float = 100.0,
        targeted_nodes: Optional[List[str]] = None
    ):
        cls._enabled = True
        cls._mode = mode
        cls._error_probability = error_probability
        cls._latency_ms = latency_ms
        cls._targeted_nodes = set(targeted_nodes) if targeted_nodes else set()

    @classmethod
    def disable(cls):
        cls._enabled = False
        cls._mode = ChaosMode.NONE
        cls._targeted_nodes.clear()

    @classmethod
    def maybe_inject_fault(cls, node_id: Optional[str] = None):
        """
        Check if chaos should be injected for the current execution step.
        Raises ChaosException if fault condition is met.
        """
        if not cls._enabled or cls._mode == ChaosMode.NONE:
            return

        if cls._targeted_nodes and node_id and node_id not in cls._targeted_nodes:
            return

        if cls._mode == ChaosMode.LATENCY_INJECTION:
            time.sleep(cls._latency_ms / 1000.0)

        elif cls._mode == ChaosMode.NETWORK_PARTITION:
            if random.random() < cls._error_probability:
                raise ChaosException(f"Simulated network partition on node '{node_id}'")

        elif cls._mode == ChaosMode.WORKER_FAILURE:
            if random.random() < cls._error_probability:
                raise ChaosException(f"Simulated worker failure/crash on node '{node_id}'")

        elif cls._mode == ChaosMode.ERROR_RATE:
            if random.random() < cls._error_probability:
                raise ChaosException(f"Simulated random transient error on node '{node_id}'")
