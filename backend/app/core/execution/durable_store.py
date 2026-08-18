import logging
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
from app.core.database import db_manager
from app.core.execution.events import ExecutionEventEnvelope
from app.core.security.context import SecurityException

logger = logging.getLogger("fluxa.durable_store")

class ExecutionSnapshot(BaseModel):
    execution_id: str
    workflow_id: str
    tenant_id: str
    variables: Dict[str, Any] = Field(default_factory=dict)
    node_states: Dict[str, str] = Field(default_factory=dict)
    memory_context: Dict[str, Any] = Field(default_factory=dict)
    agent_state: Dict[str, Any] = Field(default_factory=dict)
    timestamp: float = 0.0


class MongoDBEventStore:
    """
    Durable MongoDB Event Store managing event persistence and snapshot recovery boundaries.
    """
    @classmethod
    async def append_event(cls, event: ExecutionEventEnvelope, session: Optional[Any] = None) -> int:
        db = db_manager.db
        
        # 1. Allocate sequence atomically if not already set
        if not event.sequence:
            event.sequence = await cls.allocate_sequence(event.execution_id, session=session)
            
        event_dict = event.model_dump()
        
        # 2. Insert into execution_events collection
        try:
            await db["execution_events"].insert_one(event_dict, session=session)
        except Exception as e:
            # Check for duplicate write (idempotency key clash)
            if "duplicate key" in str(e).lower() or "e11000" in str(e).lower():
                logger.info(f"Duplicate event ignored (idempotent success): {event.event_id}")
            else:
                raise e
                
        return event.sequence

    @classmethod
    async def get_events(cls, execution_id: str, since_sequence: int = 0) -> List[ExecutionEventEnvelope]:
        db = db_manager.db
        cursor = db["execution_events"].find(
            {"execution_id": execution_id, "sequence": {"$gt": since_sequence}}
        ).sort("sequence", 1)
        
        events = []
        async for doc in cursor:
            # Remove mongo _id field
            doc.pop("_id", None)
            events.append(ExecutionEventEnvelope(**doc))
        return events

    @classmethod
    async def allocate_sequence(cls, execution_id: str, session: Optional[Any] = None) -> int:
        db = db_manager.db
        res = await db["execution_sequence_counters"].find_one_and_update(
            {"execution_id": execution_id},
            {"$inc": {"sequence": 1}},
            upsert=True,
            return_document=True,
            session=session
        )
        return res["sequence"]

    @classmethod
    async def save_snapshot(cls, snapshot: ExecutionSnapshot, session: Optional[Any] = None):
        db = db_manager.db
        from app.core.security.secrets import SecretRedactor
        snapshot_dict = SecretRedactor.redact(snapshot.model_dump())
        await db["execution_snapshots"].replace_one(
            {"execution_id": snapshot.execution_id},
            snapshot_dict,
            upsert=True,
            session=session
        )

    @classmethod
    async def get_snapshot(cls, execution_id: str) -> Optional[ExecutionSnapshot]:
        db = db_manager.db
        doc = await db["execution_snapshots"].find_one({"execution_id": execution_id})
        if doc:
            doc.pop("_id", None)
            return ExecutionSnapshot(**doc)
        return None

    @classmethod
    async def save_effect(cls, effect: "ExecutionEffect", session: Optional[Any] = None):
        db = db_manager.db
        effect_dict = effect.model_dump()
        await db["execution_effects"].replace_one(
            {
                "execution_id": effect.execution_id,
                "node_id": effect.node_id,
                "request_hash": effect.request_hash
            },
            effect_dict,
            upsert=True,
            session=session
        )

    @classmethod
    async def get_effect(cls, execution_id: str, node_id: str, request_hash: str) -> Optional["ExecutionEffect"]:

        db = db_manager.db
        doc = await db["execution_effects"].find_one({
            "execution_id": execution_id,
            "node_id": node_id,
            "request_hash": request_hash
        })
        if doc:
            doc.pop("_id", None)
            return ExecutionEffect(**doc)
        return None

    @classmethod
    async def setup_indexes(cls):
        """
        Setup indexes for performance, ordering, and idempotency constraints.
        """
        db = db_manager.db
        # Index on execution_id & sequence for fast query and uniqueness
        await db["execution_events"].create_index(
            [("execution_id", 1), ("sequence", 1)],
            unique=True
        )
        # Unique index on event_id to prevent duplicate event writes
        await db["execution_events"].create_index(
            "event_id",
            unique=True
        )
        # Index on execution_effects for lookup
        await db["execution_effects"].create_index(
            [("execution_id", 1), ("node_id", 1), ("request_hash", 1)],
            unique=True
        )

import uuid
import time

class ExecutionEffect(BaseModel):
    effect_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    execution_id: str
    node_id: str
    effect_type: str
    provider: str
    request_hash: str
    response: Dict[str, Any] = Field(default_factory=dict)
    status: str = "success"
    created_at: float = Field(default_factory=time.time)

