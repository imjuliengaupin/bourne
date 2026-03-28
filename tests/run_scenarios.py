"""
Scenario runner for comprehensive end-to-end testing of data processing workflows.

Executes all connector/workflow combinations to validate the complete pipeline.
Provides detailed reporting on successes, failures, and timing information.

Usage:
    python tests/run_scenarios.py                 # Run all scenarios
    python tests/run_scenarios.py --verbose       # Verbose output with details
    python tests/run_scenarios.py --filter=<name> # Run scenarios matching filter
"""

import argparse
import json
import sys
import time
from pathlib import Path
from typing import List, Optional, Tuple

from agents.coordinator_agent import CoordinatorAgent
from agents.data_ingestion_agent import DataIngestionAgent
from agents.data_storage_agent import DataStorageAgent
from agents.data_transformation_agent import DataTransformationAgent
from agents.data_validation_agent import DataValidationAgent
from agents.dataclasses.agent_context import AgentContext
from core.connector_manager import ConnectorManager
from core.dashboard import Dashboard
from core.logger import Logger
from core.workflow_manager import WorkflowManager


class ScenarioRunner:
    """Orchestrates scenario execution and reporting."""

    def __init__(self, verbose: bool = False, filter_pattern: Optional[str] = None) -> None:
        """Initialize the scenario runner.

        Args:
            verbose: Enable detailed output for each scenario
            filter_pattern: Only run scenarios matching this pattern
        """
        self.verbose: bool = verbose
        self.filter_pattern: str | None = filter_pattern
        self.results: List[Tuple[str, bool, Optional[str], float]] = []

    def load_scenarios(self) -> List[Tuple[str, str, str]]:
        """Load all scenario combinations from connector and workflow configs.

        Returns:
            List of (scenario_name, workflow_path, connector_path) tuples
        """
        scenarios: List[Tuple[str, str, str]] = []

        # Default workflow
        default_workflow = "json/workflows/default/default.json"

        # Define scenario groups
        connector_groups: dict[str, list[str]] = {
            "default": [
                "json/connectors/default/single-record.json",
                "json/connectors/default/multi-record.json",
                "json/connectors/default/single-record-nd.json",
                "json/connectors/default/multi-record-nd.json",
            ],
            "arrays": [
                "json/connectors/with-arrays/primitive-array.json",
                "json/connectors/with-arrays/object-array.json",
                "json/connectors/with-arrays/nested-array.json",
            ],
            "nested": [
                "json/connectors/with-arrays/simple-nested-1-lvl.json",
                "json/connectors/with-arrays/simple-nested-deep-2-lvls.json",
                "json/connectors/with-arrays/simple-nested-deep-7-lvls.json",
            ],
            "complex": [
                "json/connectors/with-arrays/complex-nested-deep-2-lvls.json",
                "json/connectors/with-arrays/complex-nested-object-array.json",
            ],
            "strict-mode": [
                "json/connectors/with-strict-mode/single-record-strict.json",
            ],
            "transformations": [
                "json/connectors/with-transformations/complex-array-transformation.json",
                "json/connectors/with-transformations/snakecase-transformation.json",
                "json/connectors/with-transformations/uppercase-transformation.json",
                "json/connectors/with-transformations/lowercase-transformation.json",
                "json/connectors/with-transformations/normalize-transformation.json",
                "json/connectors/with-transformations/special-keys-transformation.json",
                "json/connectors/with-transformations/camelcase-transformation.json",
                "json/connectors/with-transformations/pascalcase-transformation.json",
            ],
        }

        # Build scenario list
        for group, connectors in connector_groups.items():
            for connector_path in connectors:
                connector_name: str = Path(connector_path).stem
                scenario_name: str = f"{group}/{connector_name}"

                if self.filter_pattern and self.filter_pattern.lower() not in scenario_name.lower():
                    continue

                scenarios.append((scenario_name, default_workflow, connector_path))

        return scenarios

    def run_scenario(self, scenario_name: str, workflow_path: str, connector_path: str) -> Tuple[bool, Optional[str], float]:
        """Execute a single scenario.

        Args:
            scenario_name: Display name for the scenario
            workflow_path: Path to workflow config
            connector_path: Path to connector config

        Returns:
            Tuple of (success, error_message, execution_time)
        """
        start_time: float = time.time()

        try:
            # Load configurations
            with open(workflow_path, encoding="utf-8") as f:
                workflow = json.load(f)
            with open(connector_path, encoding="utf-8") as f:
                connector = json.load(f)

            # Setup pipeline components
            logger = Logger(max_logs=15, debug_mode_enabled=False)
            dashboard = Dashboard(logger)
            wf_mgr = WorkflowManager(logger)
            conn_mgr = ConnectorManager(logger, connector)
            ctx = AgentContext(logger, dashboard, None, wf_mgr, conn_mgr)

            # Validate and initialize
            if not wf_mgr.validate_keys_and_load_workflow_tasks(workflow):
                return False, f"{scenario_name}: Workflow validation failed", time.time() - start_time

            if not conn_mgr.validate_keys():
                return False, f"{scenario_name}: Connector validation failed", time.time() - start_time

            # Setup agents
            agents = {
                "DataIngestionAgent": DataIngestionAgent(ctx),
                "DataValidationAgent": DataValidationAgent(ctx),
                "DataTransformationAgent": DataTransformationAgent(ctx),
                "DataStorageAgent": DataStorageAgent(ctx),
            }

            # Execute workflow
            coordinator = CoordinatorAgent(ctx, agents)
            coordinator.run_workflow()

            return True, None, time.time() - start_time

        except FileNotFoundError as e:
            return False, f"{scenario_name}: File not found: {e}", time.time() - start_time
        except json.JSONDecodeError as e:
            return False, f"{scenario_name}: Invalid JSON: {e}", time.time() - start_time
        except Exception as e:
            return False, f"{scenario_name}: Execution error: {str(e)}", time.time() - start_time

    def run_all(self) -> int:
        """Execute all scenarios and generate report.

        Returns:
            Exit code (0 for success, 1 for failures)
        """
        scenarios = self.load_scenarios()

        if not scenarios:
            print("❌ No scenarios found matching filter")
            return 1

        print(f"\n{'='*70}")
        print(f"Running {len(scenarios)} scenario(s)...")
        print(f"{'='*70}\n")

        for scenario_name, workflow_path, connector_path in scenarios:
            success, error, elapsed = self.run_scenario(scenario_name, workflow_path, connector_path)
            self.results.append((scenario_name, success, error, elapsed))

            # Print result
            status = "✅" if success else "❌"
            print(f"{status} {scenario_name:<50} ({elapsed:.3f}s)")

            if self.verbose and error:
                print(f"   └─ {error}")

        # Print summary
        passed = sum(1 for _, success, _, _ in self.results if success)
        total = len(self.results)
        print(f"\n{'='*70}")
        print(f"Results: {passed}/{total} passed")
        print(f"{'='*70}\n")

        if self.verbose:
            print("Detailed Results:")
            print("-" * 70)
            for scenario_name, success, error, elapsed in self.results:
                status = "PASS" if success else "FAIL"
                print(f"{status:4} | {scenario_name:<45} | {elapsed:6.3f}s")
                if error:
                    print(f"     | {error}")
            print("-" * 70 + "\n")

        # Return exit code
        return 0 if passed == total else 1


def main() -> int:
    """Parse arguments and run scenarios."""
    parser = argparse.ArgumentParser(
        description="Run all data processing workflow scenarios",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )

    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable verbose output with detailed error messages",
    )

    parser.add_argument(
        "--filter",
        type=str,
        help="Only run scenarios matching this pattern (e.g., 'arrays', 'nested')",
    )

    args = parser.parse_args()

    runner = ScenarioRunner(verbose=args.verbose, filter_pattern=args.filter)
    return runner.run_all()


if __name__ == "__main__":
    sys.exit(main())
