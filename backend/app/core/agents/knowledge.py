from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
import math
import uuid

class Document(BaseModel):
    doc_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    title: str
    content: str
    metadata: Dict[str, Any] = Field(default_factory=dict)


class Chunk(BaseModel):
    chunk_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    doc_id: str
    content: str
    embedding: List[float] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class Citation(BaseModel):
    citation_id: str
    source_title: str
    snippet: str


class RetrievalResult(BaseModel):
    content: str
    score: float
    citation: Citation
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ChunkingPipeline:
    def __init__(self, chunk_size: int = 200, chunk_overlap: int = 50, separator: str = " "):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.separator = separator

    def split_document(self, doc: Document) -> List[Chunk]:
        words = doc.content.split(self.separator)
        chunks = []
        
        step = self.chunk_size - self.chunk_overlap
        if step <= 0:
            step = self.chunk_size

        for i in range(0, len(words), step):
            segment = words[i:i + self.chunk_size]
            content = self.separator.join(segment)
            chunks.append(
                Chunk(
                    doc_id=doc.doc_id,
                    content=content,
                    metadata={"index": len(chunks), "title": doc.title, **doc.metadata}
                )
            )
        return chunks


class LexicalFallbackEmbeddingEngine:
    """
    Computes a simplified lexical (Bag-of-Words) approximation for text representation.
    This is a lexical/BOW approximation and is not semantic embedding.
    """
    def compute_embedding(self, text: str) -> List[float]:
        # Basic word occurrence representation normalized
        words = text.lower().split()
        unique = list(set(words))
        raw = [words.count(w) for w in unique]
        total = sum(raw) or 1.0
        # Project into standard length list for comparison
        emb = [0.0] * 64
        for idx, w in enumerate(unique[:64]):
            val = words.count(w) / total
            # Simple hash to spread in list
            pos = abs(hash(w)) % 64
            emb[pos] += val
        
        # Normalize vector
        sq_sum = sum(x * x for x in emb) ** 0.5 or 1.0
        return [x / sq_sum for x in emb]


class KnowledgeLayer:
    def __init__(self, chunker: Optional[ChunkingPipeline] = None, embedding_engine: Optional[Any] = None):
        self.chunker = chunker or ChunkingPipeline()
        self.emb_engine = embedding_engine or LexicalFallbackEmbeddingEngine()
        self.documents: Dict[str, Document] = {}
        self.chunks: List[Chunk] = []

    async def ingest_document(self, title: str, content: str, metadata: Optional[Dict[str, Any]] = None) -> Document:
        doc = Document(title=title, content=content, metadata=metadata or {})
        self.documents[doc.doc_id] = doc
        
        # Split document into chunks
        new_chunks = self.chunker.split_document(doc)
        for chunk in new_chunks:
            # Generate embedding
            chunk.embedding = self.emb_engine.compute_embedding(chunk.content)
            self.chunks.append(chunk)
            
        return doc

    async def retrieve(self, query: str, limit: int = 3) -> List[RetrievalResult]:
        if not self.chunks:
            return []

        query_emb = self.emb_engine.compute_embedding(query)
        scored_chunks = []
        
        for chunk in self.chunks:
            # Cosine similarity
            if not chunk.embedding or len(chunk.embedding) != len(query_emb):
                sim = 0.0
            else:
                dot = sum(a * b for a, b in zip(chunk.embedding, query_emb))
                sim = dot  # since vectors are normalized, dot product is cosine similarity

            scored_chunks.append((sim, chunk))
            
        # Sort desc
        scored_chunks.sort(key=lambda x: x[0], reverse=True)
        
        results = []
        for rank, (score, chunk) in enumerate(scored_chunks[:limit]):
            citation = Citation(
                citation_id=f"CIT-{chunk.chunk_id[:6].upper()}",
                source_title=chunk.metadata.get("title", "Unknown"),
                snippet=chunk.content[:60] + "..."
            )
            results.append(
                RetrievalResult(
                    content=chunk.content,
                    score=score,
                    citation=citation,
                    metadata=chunk.metadata
                )
            )
        return results
