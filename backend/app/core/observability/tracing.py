import time
import uuid
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field

class TracingEvent(BaseModel):
    name: str
    timestamp: float = Field(default_factory=time.time)
    attributes: Dict[str, Any] = Field(default_factory=dict)

class TracingSpan(BaseModel):
    span_id: str = Field(default_factory=lambda: uuid.uuid4().hex[:16])
    trace_id: str = Field(default_factory=lambda: uuid.uuid4().hex[:32])
    parent_span_id: Optional[str] = None
    name: str
    start_time: float = Field(default_factory=time.time)
    end_time: Optional[float] = None
    attributes: Dict[str, Any] = Field(default_factory=dict)
    status: str = "OK"  # 'OK', 'ERROR', 'UNSET'
    events: List[TracingEvent] = Field(default_factory=list)

    def add_event(self, name: str, attributes: Optional[Dict[str, Any]] = None):
        if attributes is None:
            attributes = {}
        self.events.append(TracingEvent(name=name, attributes=attributes))

    def end(self, status: str = "OK", error_message: Optional[str] = None):
        self.end_time = time.time()
        self.status = status
        if error_message:
            self.attributes["error.message"] = error_message

    def get_duration_ms(self) -> float:
        if self.end_time is None:
            return (time.time() - self.start_time) * 1000
        return (self.end_time - self.start_time) * 1000

class TracingProvider:
    """
    OpenTelemetry-compatible distributed tracing provider for Fluxa workflows and nodes.
    """
    _spans: Dict[str, TracingSpan] = {}
    _active_spans: Dict[str, str] = {}  # trace_id -> active_span_id

    @classmethod
    def start_span(
        cls,
        name: str,
        trace_id: Optional[str] = None,
        parent_span_id: Optional[str] = None,
        attributes: Optional[Dict[str, Any]] = None
    ) -> TracingSpan:
        if attributes is None:
            attributes = {}
        if not trace_id:
            trace_id = uuid.uuid4().hex[:32]
        
        span = TracingSpan(
            name=name,
            trace_id=trace_id,
            parent_span_id=parent_span_id,
            attributes=attributes
        )
        cls._spans[span.span_id] = span
        cls._active_spans[trace_id] = span.span_id
        return span

    @classmethod
    def get_span(cls, span_id: str) -> Optional[TracingSpan]:
        return cls._spans.get(span_id)

    @classmethod
    def get_trace_spans(cls, trace_id: str) -> List[TracingSpan]:
        return [s for s in cls._spans.values() if s.trace_id == trace_id]

    @classmethod
    def clear(cls):
        cls._spans.clear()
        cls._active_spans.clear()
