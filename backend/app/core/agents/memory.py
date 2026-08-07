from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

class WorkingMemory(BaseModel):
    observations: List[str] = Field(default_factory=list)

    async def add_observation(self, obs: str):
        self.observations.append(obs)

    async def get_observations(self) -> List[str]:
        return self.observations

    async def clear(self):
        self.observations.clear()


class SessionMemory(BaseModel):
    variables: Dict[str, Any] = Field(default_factory=dict)
    history: List[Dict[str, str]] = Field(default_factory=list)

    async def set_variable(self, key: str, value: Any):
        self.variables[key] = value

    async def get_variable(self, key: str, default: Any = None) -> Any:
        return self.variables.get(key, default)

    async def add_chat_message(self, role: str, content: str):
        self.history.append({"role": role, "content": content})

    async def get_history(self) -> List[Dict[str, str]]:
        return self.history


class EpisodicMemoryRecord(BaseModel):
    session_id: str
    goal: str
    plan_summary: str
    final_answer: Optional[str]
    timestamp: float


class EpisodicMemory(BaseModel):
    episodes: List[EpisodicMemoryRecord] = Field(default_factory=list)

    async def record_episode(self, record: EpisodicMemoryRecord):
        self.episodes.append(record)

    async def search_episodes(self, query: str) -> List[EpisodicMemoryRecord]:
        # Simple string-matching/semantic placeholder search
        return [e for e in self.episodes if query.lower() in e.goal.lower() or query.lower() in (e.final_answer or "").lower()]


class MemoryRecord(BaseModel):
    key: str
    content: str
    embedding: List[float] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class BaseMemoryProvider(ABC):
    @abstractmethod
    async def add_concept(self, key: str, content: str, embedding: List[float], metadata: Optional[Dict[str, Any]] = None, tenant_id: Optional[str] = None):
        pass

    @abstractmethod
    async def query_concepts(self, embedding: List[float], limit: int = 5, tenant_id: Optional[str] = None) -> List[MemoryRecord]:
        pass


class LocalInMemoryMemory(BaseMemoryProvider):
    def __init__(self):
        self.storage: Dict[str, MemoryRecord] = {}

    async def add_concept(self, key: str, content: str, embedding: List[float], metadata: Optional[Dict[str, Any]] = None, tenant_id: Optional[str] = None):
        meta = dict(metadata or {})
        if tenant_id:
            meta["tenant_id"] = tenant_id
        self.storage[key] = MemoryRecord(key=key, content=content, embedding=embedding, metadata=meta)

    async def query_concepts(self, embedding: List[float], limit: int = 5, tenant_id: Optional[str] = None) -> List[MemoryRecord]:
        records = list(self.storage.values())
        if tenant_id:
            records = [r for r in records if r.metadata.get("tenant_id") == tenant_id]
            
        if not embedding or not records:
            return records[:limit]
        
        def similarity(rec: MemoryRecord) -> float:
            if not rec.embedding or len(rec.embedding) != len(embedding):
                return 0.0
            dot = sum(a * b for a, b in zip(rec.embedding, embedding))
            norm_a = sum(a * a for a in rec.embedding) ** 0.5
            norm_b = sum(b * b for b in embedding) ** 0.5
            return dot / (norm_a * norm_b) if norm_a and norm_b else 0.0

        records.sort(key=similarity, reverse=True)
        return records[:limit]


class LocalChromaMemory(BaseMemoryProvider):
    def __init__(self, collection_name: str = "fluxa_concepts", persist_directory: str = "./chroma_db"):
        import chromadb
        self.client = chromadb.PersistentClient(path=persist_directory)
        self.collection = self.client.get_or_create_collection(name=collection_name)

    async def add_concept(self, key: str, content: str, embedding: List[float], metadata: Optional[Dict[str, Any]] = None, tenant_id: Optional[str] = None):
        meta = dict(metadata or {})
        if tenant_id:
            meta["tenant_id"] = tenant_id
        self.collection.upsert(
            ids=[key],
            embeddings=[embedding],
            documents=[content],
            metadatas=[meta]
        )

    async def query_concepts(self, embedding: List[float], limit: int = 5, tenant_id: Optional[str] = None) -> List[MemoryRecord]:
        where_filter = {"tenant_id": tenant_id} if tenant_id else None
        results = self.collection.query(
            query_embeddings=[embedding],
            n_results=limit,
            where=where_filter
        )
        records = []
        if results and "ids" in results and results["ids"]:
            ids = results["ids"][0]
            documents = results["documents"][0] if "documents" in results and results["documents"] else []
            metadatas = results["metadatas"][0] if "metadatas" in results and results["metadatas"] else []
            
            for idx, key in enumerate(ids):
                doc_content = documents[idx] if idx < len(documents) else ""
                meta = metadatas[idx] if idx < len(metadatas) else {}
                records.append(MemoryRecord(key=key, content=doc_content, embedding=[], metadata=meta))
        return records


class MemoryLayer:
    """
    Coordinates working, session, episodic, and semantic memories.
    """
    def __init__(self, semantic_provider: Optional[BaseMemoryProvider] = None):
        self.working_memory = WorkingMemory()
        self.session_memory = SessionMemory()
        self.episodic_memory = EpisodicMemory()
        self.semantic_memory = semantic_provider or LocalInMemoryMemory()

    async def save_episode(self, session_id: str, goal: str, plan: Any, final_answer: Optional[str]):
        import time
        record = EpisodicMemoryRecord(
            session_id=session_id,
            goal=goal,
            plan_summary=f"Steps: {len(plan.steps) if plan else 0}",
            final_answer=final_answer,
            timestamp=time.time()
        )
        await self.episodic_memory.record_episode(record)
