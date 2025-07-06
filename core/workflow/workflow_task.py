
from typing import List, NotRequired, TypedDict


class WorkflowTask(TypedDict):
    task_name: str
    agent_name: str
    agent_method_name: str
    depends_on: List[str]
    requires_input: bool
    produces_output: bool
    max_retries: int
    retries_left: NotRequired[int]
    task_status: NotRequired[str]
