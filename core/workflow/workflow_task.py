
from typing import List, Optional, TypedDict


class WorkflowTask(TypedDict):

    agent_name: str
    agent_method_name: str
    task_name: str
    depends_on: Optional[List[str]]
    requires_input: Optional[bool]
    produces_output: Optional[bool]
    max_retries: Optional[int]
    retries_left: Optional[int]
    task_status: Optional[str]

    def __init__(self) -> None: ...
