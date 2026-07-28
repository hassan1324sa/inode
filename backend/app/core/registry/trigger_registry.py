from typing import Dict, Type, List, Optional, Any

class TriggerRegistry:
    """
    Platform Trigger Registry to register and retrieve Trigger classes.
    """
    _triggers: Dict[str, Type[Any]] = {}  # Type[BaseTrigger]

    @classmethod
    def register(cls, trigger_id: str, trigger_cls: Type[Any]):
        if trigger_id in cls._triggers:
            raise ValueError(f"Trigger already registered: {trigger_id}")
        cls._triggers[trigger_id] = trigger_cls

    @classmethod
    def get(cls, trigger_id: str) -> Optional[Type[Any]]:
        return cls._triggers.get(trigger_id)

    @classmethod
    def list_triggers(cls) -> List[str]:
        return list(cls._triggers.keys())

    @classmethod
    def clear(cls):
        cls._triggers.clear()
