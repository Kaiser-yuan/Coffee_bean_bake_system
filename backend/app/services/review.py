"""Review business logic."""
import logging

logger = logging.getLogger("coffee-roast.review")


def validate_reminders(reminders: list[dict]) -> None:
    """Validate reminder constraints: max 3, priorities 1-3 must be unique."""
    if len(reminders) > 3:
        raise ValueError("最多三条提醒")

    priorities = []
    for r in reminders:
        p = r.get("priority", 0)
        if p < 1 or p > 3:
            raise ValueError(f"优先级必须在 1-3 之间: {p}")
        if p in priorities:
            raise ValueError(f"优先级 {p} 重复")
        priorities.append(p)
