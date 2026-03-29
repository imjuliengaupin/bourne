"""Regression tests for DataIngestionAgent edge cases and helper behavior."""

from pathlib import Path
from unittest.mock import Mock

from agents.data_ingestion_agent import DataIngestionAgent
from core import constants
from tests.conftest import create_json_file, create_ndjson_file
from tests.test_data_ingestion_agent import create_mock_agent_context, setup_data_ingestion_agent_mocks


class TestDataIngestionAgentRegressions:
    def test_init_without_source_connector_state_defaults_to_none(self) -> None:
        agent_context = Mock()
        agent_context.source_data_connector_state = None

        agent = DataIngestionAgent(agent_context=agent_context)

        assert agent.source_type is None
        assert agent.source_path is None
        assert constants.LOCAL_FILE_TYPE in agent.supported_connectors

    def test_ingest_local_file_returns_empty_list_for_blank_ndjson(self, tmp_path: Path) -> None:
        agent = DataIngestionAgent(
            agent_context=create_mock_agent_context(
                source_type=constants.LOCAL_FILE_TYPE,
                source_path=str(tmp_path / "data.ndjson"),
            )
        )
        setup_data_ingestion_agent_mocks(agent=agent, caller_method=constants.TEST_CALLER_METHOD)

        data_file = tmp_path / "data.ndjson"
        data_file.write_text("\n\n", encoding="utf-8")

        result = agent.ingest_local_file(constants.LOCAL_FILE_TYPE, str(data_file))

        assert result == []
        agent.log_and_update_dashboard.assert_called()  # type: ignore[attr-defined]
        assert "✅ SUCCESS" in agent.log_and_update_dashboard.call_args[0][0]  # type: ignore[attr-defined]

    def test_load_local_records_reads_json_and_ndjson(self, tmp_path: Path) -> None:
        agent = DataIngestionAgent(
            agent_context=create_mock_agent_context(
                source_type=constants.LOCAL_FILE_TYPE,
                source_path=str(tmp_path / "data.json"),
            )
        )

        json_file = tmp_path / "data.json"
        ndjson_file = tmp_path / "data.ndjson"
        create_json_file(json_file, {"id": 1})
        create_ndjson_file(ndjson_file, [{"id": 1}, {"id": 2}])

        assert agent._load_local_records(json_file) == {"id": 1}
        assert agent._load_local_records(ndjson_file) == [{"id": 1}, {"id": 2}]
