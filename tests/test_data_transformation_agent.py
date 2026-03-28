"""Unit tests for DataTransformationAgent."""

from unittest.mock import Mock

import pytest

from agents.data_transformation_agent import DataTransformationAgent
from core import constants


class MockConnectorState(dict):
    """Minimal connector state test double with strict-mode support."""

    def is_strict_mode(self) -> bool:
        return bool(self.get("strict_mode", False))


@pytest.fixture
def transformation_agent_context(mock_logger: Mock) -> Mock:
    """Create a mock AgentContext configured for transformation tests."""

    agent_context = Mock()
    agent_context.logger = mock_logger
    agent_context.source_data_connector_state = MockConnectorState(
        {
            "transform_mode": constants.SNAKE_CASE_KEYS,
            "include_transformation_metadata": False,
            "strict_mode": False,
            "expected_schema": {},
        }
    )
    return agent_context


@pytest.mark.unit
@pytest.mark.agent
class TestDataTransformationAgent:
    def test_apply_data_transformation_adds_camel_case_metadata_keys(
        self,
        transformation_agent_context: Mock,
    ) -> None:
        transformation_agent_context.source_data_connector_state["transform_mode"] = constants.CAMEL_CASE_KEYS
        transformation_agent_context.source_data_connector_state["include_transformation_metadata"] = True

        agent = DataTransformationAgent(transformation_agent_context)
        agent.log_and_update_dashboard = Mock()  # type: ignore[method-assign]

        result = agent.apply_data_transformation(
            {"first_name": "Julien"},
            constants.CAMEL_CASE_KEYS,
        )

        assert result["firstName"] == "Julien"
        assert result["isTransformed"] is True
        assert isinstance(result["transformedOn"], str)
        assert "is_transformed" not in result
        assert "transformed_on" not in result

    def test_apply_data_transformation_normalize_types_stringifies_record_values(
        self,
        transformation_agent_context: Mock,
    ) -> None:
        transformation_agent_context.source_data_connector_state["transform_mode"] = constants.NORMALIZE_TYPES
        transformation_agent_context.source_data_connector_state["include_transformation_metadata"] = True

        agent = DataTransformationAgent(transformation_agent_context)
        agent.log_and_update_dashboard = Mock()  # type: ignore[method-assign]

        result = agent.apply_data_transformation(
            {"id": 123, "active": False},
            constants.NORMALIZE_TYPES,
        )

        assert result["id"] == "123"
        assert result["active"] == "False"
        assert "is_transformed" in result
        assert isinstance(result["transformed_on"], str)

    def test_transform_data_returns_warning_when_no_transform_mode_in_relaxed_mode(
        self,
        transformation_agent_context: Mock,
    ) -> None:
        transformation_agent_context.source_data_connector_state["transform_mode"] = None

        agent = DataTransformationAgent(transformation_agent_context)
        agent.log_and_update_dashboard = Mock()  # type: ignore[method-assign]

        result = agent.transform_data({"first_name": "Julien"})

        assert list(result) == [{"first_name": "Julien"}]
        assert result.bourne_status == constants.AgentTaskResult.SUCCESS_WITH_WARNINGS
