import asyncio
import heapq
import time
from enum import IntEnum, Enum
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field

class JobPriority(IntEnum):
    CRITICAL = 0
    HIGH = 1
    NORMAL = 2
    LOW = 3

class JobStatus(str, Enum):
    QUEUED = "QUEUED"
    ASSIGNED = "ASSIGNED"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"

class TaskJob(BaseModel):
    job_id: str
    workflow_id: str
    priority: JobPriority = JobPriority.NORMAL
    payload: Dict[str, Any] = Field(default_factory=dict)
    status: JobStatus = JobStatus.QUEUED
    worker_id: Optional[str] = None
    created_at: float = Field(default_factory=time.time)
    retries: int = 0
    max_retries: int = 3
    error_message: Optional[str] = None

    def __lt__(self, other: "TaskJob") -> bool:
        if self.priority == other.priority:
            return self.created_at < other.created_at
        return self.priority < other.priority

class WorkerNode(BaseModel):
    worker_id: str
    capabilities: List[str] = Field(default_factory=list)
    active_jobs: int = 0
    max_concurrency: int = 4
    is_alive: bool = True
    last_heartbeat: float = Field(default_factory=time.time)

class DistributedScheduler:
    """
    Distributed Priority Queue Scheduler for Fluxa workflows and node tasks.
    Supports priority classes, worker assignment, queue depth monitoring, and Temporal fallback.
    """
    _queue: List[TaskJob] = []
    _jobs: Dict[str, TaskJob] = {}
    _workers: Dict[str, WorkerNode] = {}

    @classmethod
    def enqueue(
        cls,
        job_id: str,
        workflow_id: str,
        priority: JobPriority = JobPriority.NORMAL,
        payload: Optional[Dict[str, Any]] = None,
        max_retries: int = 3
    ) -> TaskJob:
        if payload is None:
            payload = {}
        job = TaskJob(
            job_id=job_id,
            workflow_id=workflow_id,
            priority=priority,
            payload=payload,
            max_retries=max_retries
        )
        heapq.heappush(cls._queue, job)
        cls._jobs[job_id] = job
        return job

    @classmethod
    def register_worker(
        cls,
        worker_id: str,
        capabilities: Optional[List[str]] = None,
        max_concurrency: int = 4
    ) -> WorkerNode:
        if capabilities is None:
            capabilities = ["default"]
        worker = WorkerNode(
            worker_id=worker_id,
            capabilities=capabilities,
            max_concurrency=max_concurrency
        )
        cls._workers[worker_id] = worker
        return worker

    @classmethod
    def heartbeat(cls, worker_id: str):
        worker = cls._workers.get(worker_id)
        if worker:
            worker.is_alive = True
            worker.last_heartbeat = time.time()

    @classmethod
    def get_available_worker(cls, capability: str = "default") -> Optional[WorkerNode]:
        for worker in cls._workers.values():
            if worker.is_alive and worker.active_jobs < worker.max_concurrency:
                if capability in worker.capabilities or "default" in worker.capabilities:
                    return worker
        return None

    @classmethod
    def dispatch_next(cls, required_capability: str = "default") -> Optional[TaskJob]:
        """
        Pop the highest priority job and assign it to an available worker.
        """
        if not cls._queue:
            return None

        worker = cls.get_available_worker(required_capability)
        if not worker:
            return None

        job = heapq.heappop(cls._queue)
        job.status = JobStatus.ASSIGNED
        job.worker_id = worker.worker_id
        worker.active_jobs += 1
        return job

    @classmethod
    def complete_job(cls, job_id: str, success: bool = True, error_message: Optional[str] = None):
        job = cls._jobs.get(job_id)
        if not job:
            return
        worker = cls._workers.get(job.worker_id) if job.worker_id else None
        if worker and worker.active_jobs > 0:
            worker.active_jobs -= 1

        if success:
            job.status = JobStatus.COMPLETED
        else:
            job.retries += 1
            job.error_message = error_message
            if job.retries <= job.max_retries:
                job.status = JobStatus.QUEUED
                job.worker_id = None
                heapq.heappush(cls._queue, job)
            else:
                job.status = JobStatus.FAILED

    @classmethod
    def get_job_status(cls, job_id: str) -> Optional[JobStatus]:
        job = cls._jobs.get(job_id)
        return job.status if job else None

    @classmethod
    def get_queue_depth(cls) -> Dict[str, int]:
        depth = {
            "CRITICAL": 0,
            "HIGH": 0,
            "NORMAL": 0,
            "LOW": 0,
            "TOTAL": len(cls._queue)
        }
        for job in cls._queue:
            depth[job.priority.name] += 1
        return depth

    @classmethod
    def clear(cls):
        cls._queue.clear()
        cls._jobs.clear()
        cls._workers.clear()
