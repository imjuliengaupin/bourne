
from enum import Enum
from typing import Any, Dict, List

# Supported source data connector constants
LOCAL_FILE_TYPE: str = "local_file"

# Supported data transformation constants
LOWERCASE_KEYS: str = "lowercase_keys"
UPPERCASE_KEYS: str = "uppercase_keys"
SNAKE_CASE_KEYS: str = "snake_case_keys"
CAMEL_CASE_KEYS: str = "camel_case_keys"
PASCAL_CASE_KEYS: str = "pascal_case_keys"
NORMALIZE_TYPES: str = "normalize_types"

# ANSI color constants
ANSI_COLOR_RESET: str = "\033[0m"
ANSI_COLOR_GREEN: str = "\033[92m"
ANSI_COLOR_ORANGE: str = "\033[93m"
ANSI_COLOR_RED: str = "\033[91m"
ANSI_COLOR_CYAN: str = "\033[96m"
ANSI_COLOR_GRAY: str = "\033[90m"

# Global constants for test methods
TEST_CALLER_METHOD = "test_caller_method"
TEST_INGEST_DATA_METHOD = "test_ingest_data"
TEST_INGEST_DATA_PATH = "/test/path/data.json"


class AgentTaskResult(Enum):
    """
    Enhanced return values for agent methods to provide accurate task status.

    This replaces simple boolean returns with status-aware results that
    reflect the actual outcome including warnings and partial failures.
    """
    PENDING = "PENDING"
    IN_PROGRESS = "IN PROGRESS"
    SUCCESS = "SUCCESS"
    SUCCESS_WITH_WARNINGS = "WARNING"
    FAILED = "FAILED"
    RETRIED = "RETRIED"

    def __bool__(self) -> bool:
        """Allow AgentTaskResult to be used in boolean contexts"""
        return self != AgentTaskResult.FAILED

    @property
    def is_success(self) -> bool:
        """Check if task completed successfully (with or without warnings)"""
        return self in [AgentTaskResult.SUCCESS, AgentTaskResult.SUCCESS_WITH_WARNINGS]

    @property
    def status_string(self) -> str:
        """Get the status string for dashboard display"""
        return self.value


class DataTransformationMetadata:
    """
    Standard metadata fields automatically added by Bourne during any agent data transformation process.

    These fields serve as markers to detect when data has been processed through
    the transformation pipeline, enabling the DataValidationAgent to recreate schemas
    with updated key structures.
    """
    IS_TRANSFORMED: str = "is_transformed"
    TRANSFORMED_ON: str = "transformed_on"

    @classmethod
    def get_all_fields(cls) -> List[str]:
        """Returns all transformation metadata field names"""
        return [cls.IS_TRANSFORMED, cls.TRANSFORMED_ON]

    @classmethod
    def has_transformation_markers(cls, record: Dict[str, Any]) -> bool:
        """Check if record contains any transformation metadata markers"""
        return any(field in record for field in cls.get_all_fields())
