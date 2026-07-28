import asyncio
import logging
from typing import Callable, Coroutine, List, Any
from app.core.execution.events import ExecutionEvent

logger = logging.getLogger("fluxa.events")

class ExecutionEventBus:
    """
    Asynchronous Execution Event Bus featuring error isolation for subscribers.
    """
    _subscribers: List[Callable[[ExecutionEvent], Coroutine[Any, Any, None]]] = []

    @classmethod
    def subscribe(cls, callback: Callable[[ExecutionEvent], Coroutine[Any, Any, None]]):
        cls._subscribers.append(callback)

    @classmethod
    async def publish(cls, event: ExecutionEvent):
        tasks = []
        for sub in cls._subscribers:
            tasks.append(cls._run_subscriber(sub, event))
        if tasks:
            await asyncio.gather(*tasks)

    @classmethod
    async def _run_subscriber(cls, sub: Callable[[ExecutionEvent], Coroutine[Any, Any, None]], event: ExecutionEvent):
        try:
            await sub(event)
        except Exception as e:
            logger.exception(f"Event subscriber raised an exception: {e}")

    @classmethod
    def clear(cls):
        cls._subscribers.clear()
