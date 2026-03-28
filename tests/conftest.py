"""
Shared pytest configuration and fixtures for the Bourne project test suite.

This module provides common fixtures and utilities that can be reused across
all test files, implementing DRY principles and consistent test setup.
"""

import json
from pathlib import Path
from typing import Any, Dict, List, Union
from unittest.mock import Mock

import pytest

from agents.dataclasses.agent_context import AgentContext


@pytest.fixture
def mock_agent_context(logger: Mock) -> Mock:
    """
    Create a mock AgentContext for testing.

    Args:
        logger: Mock logger fixture

    Returns:
        Mock AgentContext with pre-configured attributes
    """

    agent_context = Mock(
        return_value=AgentContext
    )

    agent_context.logger = logger
    agent_context.workflow_id = "bourne-pytest-workflow1"
    agent_context.task_id = "bourne-pytest-task1"

    agent_context.connector_manager = Mock()

    return agent_context


@pytest.fixture
def mock_logger() -> Mock:
    """
    Create a mock logger for testing.

    Returns:
        Mock logger object with standard logging methods
    """

    logger = Mock()

    logger.info = Mock()
    logger.error = Mock()
    logger.warning = Mock()
    logger.debug = Mock()

    return logger


def assert_error_logged(logger_mock: Mock, expected_error_message: str) -> None:
    """
    Assert that an error was logged with the expected message.

    Args:
        logger_mock: Mock logger object to check
        expected_error_message: Expected error message (can be partial)
    """

    logger_mock.error.assert_called()

    error_calls: Any = logger_mock.error.call_args_list
    error_messages: List[str] = [str(call) for call in error_calls]

    # Check if any logged error message contains the expected text
    error_message_found: bool = any(expected_error_message in message for message in error_messages)

    assert error_message_found, (
        f"Expected error message '{expected_error_message}' not found in logged errors: "
        f"{error_messages}"
    )


def create_json_file(file_path: Path, data: Union[Dict[str, Any], List[Dict[str, Any]], None]) -> None:
    """
    Helper function to create a JSON file with arbitrary content for testing.

    Args:
        file_path: Path where the JSON file should be created
        data: Dictionary, list of dictionaries, or None to write as records to the JSON file
    """
    with open(file=file_path, mode='w', encoding="utf-8") as file:
        json.dump(
            obj=data,
            fp=file,
            indent=2
        )


def create_ndjson_file(file_path: Path, data: list) -> None:
    """
    Helper function to create a NDJSON file with arbitrary content for testing.

    Args:
        file_path: Path where the NDJSON file should be created
        data: List of dictionaries to write as records to the NDJSON file
    """
    with open(file=file_path, mode='w', encoding="utf-8") as file:
        for record in data:
            file.write(f"{json.dumps(record)}\n")


def create_text_file(file_path: Path, data: str) -> None:
    """
    Helper function to create a text file with arbitrary content for testing.

    Args:
        file_path: Path where the text file should be created
        data: Raw text content to write to the file
    """
    with open(file=file_path, mode='w', encoding="utf-8") as file:
        file.write(data)


def pytest_configure(config) -> None:
    """Configure custom pytest markers."""
    config.addinivalue_line("markers", "unit: mark test as a unit test")
    config.addinivalue_line("markers", "agent: mark test as agent-specific")
