"""
Unit tests for DataIngestionAgent.

This module tests the data ingestion functionality including:
- Agent initialization
- Data ingestion from local files (JSON, NDJSON)
- Error handling for missing files and invalid formats
"""

from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union
from unittest.mock import Mock

import pytest

from agents.data_ingestion_agent import DataIngestionAgent
from agents.dataclasses.agent_context import AgentContext
from core import constants
from tests.conftest import (create_json_file, create_ndjson_file,
                            create_text_file)


def create_mock_agent_context(source_type: str, source_path: str) -> Mock:
    """
    Helper function to create a mock AgentContext with data ingestion specific configurations.

    Args:
        source_type: The type of data source
        source_path: Path to the data source

    Returns:
        Mock AgentContext configured for data ingestion testing
    """

    mock_agent_context: Mock = Mock(
        return_value=AgentContext
    )

    source_data_connector_state: Dict[str, str] = {
        "source_type": source_type,
        "source_path": source_path
    }

    mock_agent_context.source_data_connector_state = source_data_connector_state

    return mock_agent_context


def setup_data_ingestion_agent_mocks(agent: DataIngestionAgent, caller_method: str) -> None:
    """
    Set up mocks specific to DataIngestionAgent testing.

    Args:
        agent: The DataIngestionAgent instance to mock
        caller_method: The method name to return from get_caller_method mock
    """
    agent.log_and_update_dashboard = Mock()  # type: ignore[method-assign]

    agent.get_caller_method = Mock(  # type: ignore[method-assign]
        return_value=caller_method
    )


def assert_data_ingestion_error_logged(agent: DataIngestionAgent, expected_error_text: str) -> None:
    """
    Assert that a data ingestion specific error was logged with expected message.

    Args:
        agent: The DataIngestionAgent instance with mocked logging
        expected_error_text: Text that should appear in the error message

    NOTE:
        Static type checker (mypy) limitation with Mock attribute access

        Problem:
            Static type checkers cannot validate attributes dynamically assigned to Mock objects during test setup.
            The `log_and_update_dashboard` attribute is assigned via `Mock()` at runtime in the `setup_data_ingestion_agent_mocks()` method.

        Runtime behavior:
            This works perfectly at runtime because Mock objects allow dynamic attribute assignment.
            The type ignore only suppresses static analysis (mypy) limitation.
    """

    # Verify logging method was called and extract message content
    agent.log_and_update_dashboard.assert_called()  # type: ignore[attr-defined]

    # Verify error message contains expected content
    call_args: str = agent.log_and_update_dashboard.call_args[0][0]  # type: ignore[attr-defined]
    assert "❌ FAILURE" in call_args
    assert expected_error_text in call_args


@pytest.mark.unit
@pytest.mark.agent
class TestDataIngestionAgent:
    """Test suite for the DataIngestionAgent class."""

    @pytest.fixture
    def mock_local_file_context(self) -> Mock:
        """Create a mock AgentContext for local file testing."""
        return create_mock_agent_context(
            source_type=constants.LOCAL_FILE_TYPE,
            source_path=constants.TEST_INGEST_DATA_PATH
        )

    # REVIEW: @pytest.fixture
    # def mock_s3_context(self) -> Mock:
    #     """Create a mock AgentContext for Amazon Web Services (AWS) S3 testing."""
    #     return create_mock_agent_context(constants.AMAZON_S3_TYPE, "s3://test-bucket/data.json")

    # REVIEW: @pytest.fixture
    # def mock_database_context(self) -> Mock:
    #     """Create a mock AgentContext for PostgreSQL database testing."""
    #     return create_mock_agent_context(constants.POSTGRESQL_TYPE, "postgresql://user:pass@localhost/db")

    def test_init_with_valid_context(self, mock_local_file_context: Mock) -> None:
        """
        Test agent initialization with valid context.

        WHAT: Tests that the agent correctly initializes with proper values
        WHY: Ensures the constructor sets up the agent state correctly
        HOW: Creates agent and checks instance variables
        """

        # Arrange
        # mock_local_file_context provided by fixture

        # Act
        agent: DataIngestionAgent = DataIngestionAgent(
            agent_context=mock_local_file_context
        )

        # Assert
        assert constants.LOCAL_FILE_TYPE in agent.supported_connectors
        assert agent.source_type == constants.LOCAL_FILE_TYPE
        assert agent.source_path == constants.TEST_INGEST_DATA_PATH

    def test_init_with_missing_source_type(self) -> None:
        """
        Test initialization when source_type is missing.

        WHAT: Tests behavior when required configuration is missing
        WHY: Ensures graceful handling of incomplete configuration
        HOW: Creates context without source_type, checks None assignment
        """

        # Arrange
        mock_agent_context: Mock = create_mock_agent_context(
            source_type=constants.LOCAL_FILE_TYPE,
            source_path=constants.TEST_INGEST_DATA_PATH
        )

        mock_agent_context.source_data_connector_state = {}  # Override to be empty for this test

        # Act
        agent: DataIngestionAgent = DataIngestionAgent(
            agent_context=mock_agent_context
        )

        # Assert
        assert agent.source_type is None
        assert agent.source_path is None


@pytest.mark.unit
@pytest.mark.agent
class TestIngestData:
    """Test suite for the main agent method `ingest_data()`."""

    def test_ingest_data_calls_local_file_method(self) -> None:
        """
        Test that agent method `ingest_data()` properly delegates to the `ingest_local_file()` method.

        WHAT: Tests the main entry point method
        WHY: Ensures proper method delegation and integration
        HOW: Mock the `ingest_local_file()` method and verify it's called
        """

        # Arrange
        agent: DataIngestionAgent = DataIngestionAgent(
            agent_context=create_mock_agent_context(
                source_type=constants.LOCAL_FILE_TYPE,
                source_path=constants.TEST_INGEST_DATA_PATH
            )
        )

        setup_data_ingestion_agent_mocks(
            agent=agent,
            caller_method=constants.TEST_INGEST_DATA_METHOD
        )

        agent.ingest_local_file = Mock(  # type: ignore[method-assign]
            return_value={"key": "value"}
        )

        # Act
        result: Optional[Union[Dict[str, Any], List[Dict[str, Any]]]] = agent.ingest_data()

        # Assert
        assert result == {"key": "value"}

        agent.ingest_local_file.assert_called_once_with(
            constants.LOCAL_FILE_TYPE,
            constants.TEST_INGEST_DATA_PATH
        )

    def test_ingest_data_with_unsupported_connector(self) -> None:
        """
        Test behavior with unsupported source data type connectors.

        WHAT: Tests error handling for unknown connector types
        WHY: Ensures graceful failure for unsupported data sources
        HOW: Set invalid source_type, expect None result
        """

        # Arrange
        agent: DataIngestionAgent = DataIngestionAgent(
            agent_context=create_mock_agent_context(
                source_type="unsupported_source_type",
                source_path=constants.TEST_INGEST_DATA_PATH)
        )

        setup_data_ingestion_agent_mocks(
            agent=agent,
            caller_method=constants.TEST_INGEST_DATA_METHOD
        )

        # Act
        result: Optional[Union[Dict[str, Any], List[Dict[str, Any]]]] = agent.ingest_data()

        # Assert
        assert result is None

        assert_data_ingestion_error_logged(
            agent=agent,
            expected_error_text="Unknown source data connector"
        )

    def test_ingest_data_handles_exceptions(self) -> None:
        """
        Test exception handling in agent method `ingest_data()`.

        WHAT: Tests that exceptions are caught and logged properly
        WHY: Ensures robust error handling at the main entry point
        HOW: Force an exception in the `ingest_local_file()` method, verify graceful handling
        """

        # Arrange
        agent: DataIngestionAgent = DataIngestionAgent(
            agent_context=create_mock_agent_context(
                source_type=constants.LOCAL_FILE_TYPE,
                source_path=constants.TEST_INGEST_DATA_PATH
            )
        )

        setup_data_ingestion_agent_mocks(
            agent=agent,
            caller_method=constants.TEST_INGEST_DATA_METHOD
        )

        agent.ingest_local_file = Mock(  # type: ignore[method-assign]
            side_effect=Exception("Test exception for error handling validation")
        )

        # Act
        result: Optional[Union[Dict[str, Any], List[Dict[str, Any]]]] = agent.ingest_data()

        # Assert
        assert result is None

        assert_data_ingestion_error_logged(
            agent=agent,
            expected_error_text="Test exception for error handling validation"
        )


@pytest.mark.unit
@pytest.mark.agent
class TestIngestLocalFile:
    """Test suite for the `ingest_local_file()` method."""

    @pytest.fixture
    def agent_with_tmp_files(self, tmp_path: Path) -> Tuple[DataIngestionAgent, Path]:
        """
        Create agent with temporary files for testing.

        This fixture creates real temporary files on the local file system
        that are used for testing file operations safely. Cleanup handled by pytest.
        """

        # Create agent with temp file context
        agent: DataIngestionAgent = DataIngestionAgent(
            agent_context=create_mock_agent_context(
                source_type=constants.LOCAL_FILE_TYPE,
                source_path=f"{tmp_path}/data.json"
            )
        )

        # Set up common mocks using helper function
        setup_data_ingestion_agent_mocks(
            agent=agent,
            caller_method=constants.TEST_CALLER_METHOD
        )

        return agent, tmp_path

    def test_ingest_json_file_single_record(self, agent_with_tmp_files: Tuple[DataIngestionAgent, Path]) -> None:
        """
        Test ingesting a JSON file with a single record.

        WHAT: Tests reading a simple JSON object from file
        WHY: Most common use case is a single JSON object
        HOW: Create temp JSON file, call `ingest_local_file()` method, verify result

        NOTE:
            Static type checker (mypy) limitation with Mock attribute access

            Problem:
                Static type checkers cannot validate attributes dynamically assigned to Mock objects during test setup.
                The `log_and_update_dashboard` attribute is assigned via `Mock()` at runtime in the `setup_data_ingestion_agent_mocks()` method.

            Runtime behavior:
                This works perfectly at runtime because Mock objects allow dynamic attribute assignment.
                The type ignore only suppresses static analysis (mypy) limitation.
        """

        # Arrange
        agent, tmp_path = agent_with_tmp_files
        test_data_file: Path = tmp_path / "data.json"
        test_data: Dict[str, Union[str, int]] = {
            "ID": 1, "Timestamp": "2099-01-01 00:00:00"
        }

        # Act
        create_json_file(
            file_path=test_data_file,
            data=test_data
        )

        result: Optional[Union[Dict[str, Any], List[Dict[str, Any]]]] = agent.ingest_local_file(
            source_type=constants.LOCAL_FILE_TYPE,
            source_path=str(test_data_file)
        )

        # Assert
        assert result == test_data
        assert isinstance(result, dict)
        assert len(result) == 2  # Dictionary has 2 keys: ID and Timestamp

        # Verify logging method was called and extract message content
        agent.log_and_update_dashboard.assert_called()  # type: ignore[attr-defined]

    def test_ingest_json_file_multiple_records(self, agent_with_tmp_files: Tuple[DataIngestionAgent, Path]) -> None:
        """
        Test ingesting a JSON file with multiple records (array).

        WHAT: Tests reading JSON array from file
        WHY: Common use case, multiple records in array format
        HOW: Create temp JSON array file, verify result is list
        """

        # Arrange
        agent, tmp_path = agent_with_tmp_files
        test_data_file: Path = tmp_path / "data.json"
        test_data: List[Dict[str, Union[int, str]]] = [
            {"ID": 1, "Timestamp": "2099-01-01 00:00:00"},
            {"ID": 2, "Timestamp": "2099-01-01 00:00:00"},
            {"ID": 3, "Timestamp": "2099-01-01 00:00:00"}
        ]

        # Act
        create_json_file(
            file_path=test_data_file,
            data=test_data
        )

        result: Optional[Union[Dict[str, Any], List[Dict[str, Any]]]] = agent.ingest_local_file(
            source_type=constants.LOCAL_FILE_TYPE,
            source_path=str(test_data_file)
        )

        # Assert
        assert result == test_data
        assert isinstance(result, list)
        assert len(result) == 3

    def test_ingest_ndjson_file(self, agent_with_tmp_files: Tuple[DataIngestionAgent, Path]) -> None:
        """
        Test ingesting an NDJSON (newline-delimited JSON) file.

        WHAT: Tests reading NDJSON format (one JSON object per line)
        WHY: NDJSON is common for streaming/big data scenarios
        HOW: Create temp NDJSON file, verify result is list of objects
        """

        # Arrange
        agent, tmp_path = agent_with_tmp_files
        test_data_file: Path = tmp_path / "data.ndjson"
        test_data: List[Dict[str, Union[int, str]]] = [
            {"ID": 1, "Timestamp": "2099-01-01 00:00:00"},
        ]

        # Act
        create_ndjson_file(
            file_path=test_data_file,
            data=test_data
        )

        result: Optional[Union[Dict[str, Any], List[Dict[str, Any]]]] = agent.ingest_local_file(
            source_type=constants.LOCAL_FILE_TYPE,
            source_path=str(test_data_file)
        )

        # Assert
        assert result == test_data
        assert isinstance(result, list)
        assert len(result) == 1

    def test_ingest_nonexistent_file(self, agent_with_tmp_files: Tuple[DataIngestionAgent, Path]) -> None:
        """
        Test behavior when trying to ingest a file that doesn't exist.

        WHAT: Tests error handling for missing files
        WHY: Common error case, ensures graceful failure
        HOW: Call `ingest_local_file()` method with non-existent path, expect None
        """

        # Arrange
        agent, tmp_path = agent_with_tmp_files
        nonexistent_data_file: Path = tmp_path / "data.json"

        # Act
        result: Optional[Union[Dict[str, Any], List[Dict[str, Any]]]] = agent.ingest_local_file(
            source_type=constants.LOCAL_FILE_TYPE,
            source_path=str(nonexistent_data_file)
        )

        # Assert
        assert result is None

        assert_data_ingestion_error_logged(
            agent=agent,
            expected_error_text="not found"
        )

    def test_ingest_invalid_json_file(self, agent_with_tmp_files: Tuple[DataIngestionAgent, Path]) -> None:
        """
        Test behavior when trying to ingest malformed JSON.

        WHAT: Tests error handling for corrupted/invalid JSON files
        WHY: Real-world files can be corrupted and need graceful handling
        HOW: Create file with invalid JSON, expect None result
        """

        # Arrange
        agent, tmp_path = agent_with_tmp_files
        test_data_file: Path = tmp_path / "data.json"

        # Act
        create_text_file(
            file_path=test_data_file,
            data="{broken: 'malformed json content'}"  # Invalid JSON content
        )

        result: Optional[Union[Dict[str, Any], List[Dict[str, Any]]]] = agent.ingest_local_file(
            source_type=constants.LOCAL_FILE_TYPE,
            source_path=str(test_data_file)
        )

        # Assert
        assert result is None

        assert_data_ingestion_error_logged(
            agent=agent,
            expected_error_text="❌ FAILURE"
        )

    def test_ingest_empty_json_file(self, agent_with_tmp_files: Tuple[DataIngestionAgent, Path]) -> None:
        """
        Test ingesting an empty JSON file.

        WHAT: Tests behavior with empty files
        WHY: Edge case that can occur in real-world scenarios
        HOW: Create empty file, verify None result and appropriate logging

        NOTE:
            Static type checker (mypy) limitation with Mock attribute access

            Problem:
                Static type checkers cannot validate attributes dynamically assigned to Mock objects during test setup.
                The `log_and_update_dashboard` attribute is assigned via `Mock()` at runtime in the `setup_data_ingestion_agent_mocks()` method.

            Runtime behavior:
                This works perfectly at runtime because Mock objects allow dynamic attribute assignment.
                The type ignore only suppresses static analysis (mypy) limitation.
        """

        # Arrange
        agent, tmp_path = agent_with_tmp_files
        test_data_file: Path = tmp_path / "data.json"

        # Act
        test_data_file.touch()  # Create empty file and get path in one line

        result: Optional[Union[Dict[str, Any], List[Dict[str, Any]]]] = agent.ingest_local_file(
            source_type=constants.LOCAL_FILE_TYPE,
            source_path=str(test_data_file)
        )

        # Assert
        assert result is None

        # Verify logging method was called and extract message content
        agent.log_and_update_dashboard.assert_called()  # type: ignore[attr-defined]

    def test_ingest_json_file_with_null_content(self, agent_with_tmp_files: Tuple[DataIngestionAgent, Path]) -> None:
        """
        Test ingesting a JSON file containing null content.

        WHAT: Tests behavior when JSON file contains valid JSON null value
        WHY: Edge case where `json.load()` succeeds but returns None
        HOW: Create file with null content, verify None result and warning logged

        NOTE:
            Static type checker (mypy) limitation with Mock attribute access

            Problem:
                Static type checkers cannot validate attributes dynamically assigned to Mock objects during test setup.
                The `log_and_update_dashboard` attribute is assigned via `Mock()` at runtime in the `setup_data_ingestion_agent_mocks()` method.

            Runtime behavior:
                This works perfectly at runtime because Mock objects allow dynamic attribute assignment.
                The type ignore only suppresses static analysis (mypy) limitation.
        """

        # Arrange
        agent, tmp_path = agent_with_tmp_files
        test_data_file: Path = tmp_path / "data.json"

        # Act
        create_json_file(
            file_path=test_data_file,
            data=None  # Valid JSON null value
        )

        result: Optional[Union[Dict[str, Any], List[Dict[str, Any]]]] = agent.ingest_local_file(
            source_type=constants.LOCAL_FILE_TYPE,
            source_path=str(test_data_file)
        )

        # Assert
        assert result is None

        # Verify logging method was called and extract message content
        agent.log_and_update_dashboard.assert_called()  # type: ignore[attr-defined]

        # Verify warning message contains expected content
        call_args: str = agent.log_and_update_dashboard.call_args[0][0]  # type: ignore[attr-defined]
        assert "⚠️ WARNING" in call_args
        assert "No data provided, empty structure found" in call_args


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
