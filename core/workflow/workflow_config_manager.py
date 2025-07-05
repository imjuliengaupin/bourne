
from typing import Any, Dict, List, Optional


class WorkflowConfigManager:

    def __init__(self, workflow_plan_conf: Dict[str, Any]) -> None:
        self.workflow_plan_conf: Dict[str, Any] = workflow_plan_conf if isinstance(workflow_plan_conf, dict) else {}
        self.required_keys: List[str] = [
            "source_type",
            "source_path",
            "transform_mode",
            "transform_output_path",
            # optionally: "expected_schema"
        ]

    def get(self, key: str) -> Optional[Any]:
        return self.workflow_plan_conf.get(key)

    def validate_keys(self) -> bool:
        return all(key in self.workflow_plan_conf for key in self.required_keys)
