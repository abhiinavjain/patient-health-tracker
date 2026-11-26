from .base import Task, TaskData
from .chronic import CVDRiskTask, DiabetesRiskTask
from .readmission import ReadmissionTask

TASKS: dict[str, type[Task]] = {
    "readmission_30d": ReadmissionTask,
    "diabetes_risk": DiabetesRiskTask,
    "cvd_risk": CVDRiskTask,
}


def get_task(name: str) -> Task:
    try:
        return TASKS[name]()
    except KeyError:
        raise ValueError(f"Unknown task {name!r}; choose from {sorted(TASKS)}") from None


__all__ = ["TASKS", "Task", "TaskData", "get_task"]
