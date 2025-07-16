
from typing import Any, Dict, List, Optional

from core.logger import Logger


class ConnectorManager:

    def __init__(self, logger: Logger, source_data_connector: Optional[Dict[str, Any]]) -> None:
        self.logger: Logger = logger
        self.source_data_connector: Dict[str, Any] = source_data_connector if source_data_connector and isinstance(source_data_connector, dict) else {}
        self.required_keys: List[str] = [
            "source_type",
            "source_path",
            "expected_schema",
            # optional: "transform_mode",
            # optional: "transform_output_path",
        ]

    def get_class_label(self) -> str:
        return type(self).__name__

    def get(self, key: str) -> Optional[Any]:
        return self.source_data_connector.get(key)

    def validate_keys(self) -> bool:
        missing_keys: List[str] = [key for key in self.required_keys if key not in self.source_data_connector]

        if missing_keys:
            self.logger.log(self.get_class_label(), f"❌ FAILURE: The source data connector configurations are missing required keys {missing_keys}. Exiting...")
            return False

        return True
