import time
import uuid
import copy
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field

class SnapshotBackup(BaseModel):
    snapshot_id: str = Field(default_factory=lambda: f"snap-{uuid.uuid4().hex[:8]}")
    timestamp: float = Field(default_factory=time.time)
    region: str = "us-east-1"
    workflow_states: Dict[str, Any] = Field(default_factory=dict)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    is_replicated: bool = False
    replicated_regions: List[str] = Field(default_factory=list)

class RestoreReport(BaseModel):
    success: bool
    snapshot_id: str
    restored_workflows: int
    target_region: str
    error_message: Optional[str] = None

class DisasterRecoveryManager:
    """
    Manages automated snapshot backups, point-in-time recovery, and cross-region replication.
    """
    _snapshots: Dict[str, SnapshotBackup] = {}
    _regional_store: Dict[str, Dict[str, SnapshotBackup]] = {}

    @classmethod
    def create_snapshot(
        cls,
        workflow_states: Dict[str, Any],
        region: str = "us-east-1",
        metadata: Optional[Dict[str, Any]] = None
    ) -> SnapshotBackup:
        if metadata is None:
            metadata = {}
        snap = SnapshotBackup(
            region=region,
            workflow_states=copy.deepcopy(workflow_states),
            metadata=metadata
        )
        cls._snapshots[snap.snapshot_id] = snap
        if region not in cls._regional_store:
            cls._regional_store[region] = {}
        cls._regional_store[region][snap.snapshot_id] = snap
        return snap

    @classmethod
    def replicate_to_region(cls, snapshot_id: str, target_region: str) -> bool:
        """
        Replicate a snapshot to another geographic region for disaster recovery.
        """
        snap = cls._snapshots.get(snapshot_id)
        if not snap:
            return False
        
        replica = copy.deepcopy(snap)
        replica.region = target_region
        snap.is_replicated = True
        if target_region not in snap.replicated_regions:
            snap.replicated_regions.append(target_region)

        if target_region not in cls._regional_store:
            cls._regional_store[target_region] = {}
        cls._regional_store[target_region][snapshot_id] = replica
        return True

    @classmethod
    def restore_snapshot(cls, snapshot_id: str, target_region: str = "us-east-1") -> RestoreReport:
        """
        Perform point-in-time recovery of workflow states from a regional snapshot.
        """
        region_snaps = cls._regional_store.get(target_region, {})
        snap = region_snaps.get(snapshot_id) or cls._snapshots.get(snapshot_id)
        
        if not snap:
            return RestoreReport(
                success=False,
                snapshot_id=snapshot_id,
                restored_workflows=0,
                target_region=target_region,
                error_message=f"Snapshot '{snapshot_id}' not found in region '{target_region}'"
            )

        restored_count = len(snap.workflow_states)
        return RestoreReport(
            success=True,
            snapshot_id=snapshot_id,
            restored_workflows=restored_count,
            target_region=target_region
        )

    @classmethod
    def list_snapshots(cls, region: Optional[str] = None) -> List[SnapshotBackup]:
        if region:
            return list(cls._regional_store.get(region, {}).values())
        return list(cls._snapshots.values())

    @classmethod
    def clear(cls):
        cls._snapshots.clear()
        cls._regional_store.clear()
