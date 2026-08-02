import pytest
import time
from app.core.execution.scheduler import (
    DistributedScheduler,
    JobPriority,
    JobStatus,
    TaskJob
)
from app.core.observability import FluxaMetrics, TracingProvider
from app.core.resilience import (
    ChaosSimulator,
    ChaosMode,
    ChaosException,
    DisasterRecoveryManager
)

@pytest.fixture(autouse=True)
def clean_phase12_state():
    DistributedScheduler.clear()
    FluxaMetrics.clear()
    TracingProvider.clear()
    ChaosSimulator.disable()
    DisasterRecoveryManager.clear()
    yield
    DistributedScheduler.clear()
    FluxaMetrics.clear()
    TracingProvider.clear()
    ChaosSimulator.disable()
    DisasterRecoveryManager.clear()

# --- DISTRIBUTED SCHEDULER TESTS ---

def test_scheduler_priority_ordering_and_worker_dispatch():
    # Register worker
    worker = DistributedScheduler.register_worker("worker-1", capabilities=["default", "gpu"], max_concurrency=2)

    # Enqueue normal job first, then critical job
    job_normal = DistributedScheduler.enqueue(
        job_id="job-normal",
        workflow_id="wf-1",
        priority=JobPriority.NORMAL,
        payload={"task": "normal"}
    )
    job_critical = DistributedScheduler.enqueue(
        job_id="job-critical",
        workflow_id="wf-1",
        priority=JobPriority.CRITICAL,
        payload={"task": "critical"}
    )

    depth = DistributedScheduler.get_queue_depth()
    assert depth["TOTAL"] == 2
    assert depth["CRITICAL"] == 1
    assert depth["NORMAL"] == 1

    # First dispatch should grab CRITICAL job even though NORMAL was enqueued earlier
    dispatched_1 = DistributedScheduler.dispatch_next()
    assert dispatched_1 is not None
    assert dispatched_1.job_id == "job-critical"
    assert dispatched_1.status == JobStatus.ASSIGNED
    assert worker.active_jobs == 1

    # Second dispatch should grab NORMAL job
    dispatched_2 = DistributedScheduler.dispatch_next()
    assert dispatched_2 is not None
    assert dispatched_2.job_id == "job-normal"
    assert worker.active_jobs == 2

    # Complete critical job
    DistributedScheduler.complete_job("job-critical", success=True)
    assert DistributedScheduler.get_job_status("job-critical") == JobStatus.COMPLETED
    assert worker.active_jobs == 1

def test_scheduler_retry_on_failure():
    DistributedScheduler.register_worker("worker-retry", max_concurrency=2)
    job = DistributedScheduler.enqueue(
        "job-fail",
        workflow_id="wf-fail",
        priority=JobPriority.HIGH,
        max_retries=1
    )

    # First attempt -> Fails
    dispatched = DistributedScheduler.dispatch_next()
    assert dispatched.job_id == "job-fail"
    DistributedScheduler.complete_job("job-fail", success=False, error_message="Network glitch")

    # Should be re-queued because max_retries=1
    assert job.status == JobStatus.QUEUED
    assert job.retries == 1
    assert DistributedScheduler.get_queue_depth()["TOTAL"] == 1

    # Second attempt -> Fails again -> Exceeds max_retries
    dispatched_again = DistributedScheduler.dispatch_next()
    DistributedScheduler.complete_job("job-fail", success=False, error_message="Fatal error")
    assert job.status == JobStatus.FAILED
    assert job.retries == 2

# --- OBSERVABILITY METRICS & TRACING TESTS ---

def test_prometheus_metrics_export():
    FluxaMetrics.inc_counter("workflow_executions_total", 1, labels={"status": "success"})
    FluxaMetrics.set_gauge("active_workers", 5.0)
    FluxaMetrics.observe_histogram("node_execution_duration_seconds", 0.45, labels={"node_type": "llm"})
    
    prom_text = FluxaMetrics.export_prometheus()
    assert "# TYPE workflow_executions_total counter" in prom_text
    assert 'workflow_executions_total{status="success"} 1' in prom_text
    assert "# TYPE active_workers gauge" in prom_text
    assert "active_workers 5.0" in prom_text
    assert "# TYPE node_execution_duration_seconds histogram" in prom_text
    assert 'node_execution_duration_seconds_count{node_type="llm"} 1' in prom_text

def test_opentelemetry_tracing():
    root_span = TracingProvider.start_span("root_workflow_span", attributes={"workflow_id": "wf-100"})
    assert root_span.status == "OK"

    child_span = TracingProvider.start_span(
        "llm_node_span",
        trace_id=root_span.trace_id,
        parent_span_id=root_span.span_id
    )
    child_span.add_event("prompt_sent", {"tokens": 128})
    child_span.end(status="OK")
    root_span.end(status="OK")

    trace_spans = TracingProvider.get_trace_spans(root_span.trace_id)
    assert len(trace_spans) == 2
    assert child_span.get_duration_ms() >= 0.0
    assert len(child_span.events) == 1

# --- CHAOS SIMULATOR TESTS ---

def test_chaos_simulator_fault_injection():
    ChaosSimulator.enable(
        mode=ChaosMode.NETWORK_PARTITION,
        error_probability=1.0,
        targeted_nodes=["target_node_1"]
    )

    # Untargeted node -> No exception
    ChaosSimulator.maybe_inject_fault("safe_node")

    # Targeted node -> Raises ChaosException
    with pytest.raises(ChaosException, match="network partition"):
        ChaosSimulator.maybe_inject_fault("target_node_1")

    ChaosSimulator.disable()
    # After disabling -> No exception
    ChaosSimulator.maybe_inject_fault("target_node_1")

# --- DISASTER RECOVERY TESTS ---

def test_disaster_recovery_snapshot_replication_and_restore():
    workflow_state = {
        "wf-101": {"status": "COMPLETED", "result": 42},
        "wf-102": {"status": "RUNNING", "step": 3}
    }

    # 1. Create Snapshot
    snap = DisasterRecoveryManager.create_snapshot(
        workflow_states=workflow_state,
        region="us-east-1",
        metadata={"creator": "auto-backup"}
    )
    assert snap.snapshot_id in [s.snapshot_id for s in DisasterRecoveryManager.list_snapshots("us-east-1")]

    # 2. Replicate across regions
    replicated = DisasterRecoveryManager.replicate_to_region(snap.snapshot_id, target_region="eu-west-1")
    assert replicated is True

    # Check both regions
    east_snaps = DisasterRecoveryManager.list_snapshots("us-east-1")
    eu_snaps = DisasterRecoveryManager.list_snapshots("eu-west-1")
    assert len(east_snaps) == 1
    assert len(eu_snaps) == 1
    assert eu_snaps[0].region == "eu-west-1"

    # 3. Restore in eu-west-1
    report = DisasterRecoveryManager.restore_snapshot(snap.snapshot_id, target_region="eu-west-1")
    assert report.success is True
    assert report.restored_workflows == 2
    assert report.target_region == "eu-west-1"
