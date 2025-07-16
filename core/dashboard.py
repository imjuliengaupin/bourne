
from typing import Dict, List, Optional, Tuple

from rich.columns import Columns
from rich.console import Console
from rich.panel import Panel
from rich.style import Style
from rich.table import Table
from rich.text import Text

from core import constants
from core.logger import Logger
from core.workflow_task import WorkflowTask


class Dashboard:

    COLUMN_DEFINITIONS: List[Tuple[str, str]] = [
        ("TASK NAME", "task_name"),
        ("AGENT", "agent_name"),
        ("METHOD TO RUN", "agent_method_name"),
        ("STATUS", "task_status"),
        ("RETRIES LEFT", "retries_left"),
    ]

    STATUS_STYLES: Dict[str, Style] = {
        constants.STATUS_SUCCESS: Style(color="green", bold=True),
        constants.STATUS_IN_PROGRESS: Style(color="blue", bold=True),
        constants.STATUS_FAILED: Style(color="red", bold=True),
        constants.STATUS_RETRIED: Style(color="orange3", bold=True),
        constants.STATUS_PENDING: Style(color="bright_black", bold=True),
    }

    def __init__(self, logger: Logger) -> None:
        logger.log("Dashboard", "ℹ️ INFO: Initializing dashboard...")

        self.console: Console = Console()
        self.max_logs: int = logger.max_logs

    def render(self, tasks: List[WorkflowTask], logs: List[str], data_before_transformation: Optional[dict] = None, data_after_transformation: Optional[dict] = None) -> Columns:
        panels: list = [self.create_tasks_table(tasks), self.create_logs_panel(logs)]

        if data_before_transformation is not None and data_after_transformation is not None:
            panels.append(self.create_data_preview_panel(data_before_transformation, data_after_transformation))

        return Columns(panels)

    def get_status_style(self, status: Optional[str]) -> Style:
        return self.STATUS_STYLES.get(str(status))

    def create_tasks_table(self, workflow_tasks: List[WorkflowTask]) -> Table:
        tasks_table: Table = Table(
            show_header=True,
            header_style="bold blue",
            border_style="blue",
        )

        for header, _ in self.COLUMN_DEFINITIONS:
            tasks_table.add_column(header, justify="left", no_wrap=True)

        for task in workflow_tasks:
            row_values: list = []

            for _, key in self.COLUMN_DEFINITIONS:
                if key == "task_name":
                    value: str = str(task.get("task_name"))
                elif key == "agent_name":
                    value: str = str(task.get("agent_name"))
                elif key == "agent_method_name":
                    value: str = str(task.get("agent_method_name"))
                elif key == "task_status":
                    value: str = str(task.get("task_status"))
                elif key == "retries_left":
                    value: str = str(task.get("retries_left"))
                else:
                    value: str = ""

                if key == "task_status":
                    style: Style = self.get_status_style(task.get("task_status"))
                    row_values.append(Text(value, style=style))
                else:
                    row_values.append(Text(value))

            tasks_table.add_row(*row_values)

        return tasks_table

    def create_logs_panel(self, logs: List[str]) -> Panel:
        log_message: str = "\n".join(logs)

        # Define a fixed height for the panel to match the max_logs setting, +2 for top/bottom borders
        height: int = self.max_logs + 2

        return Panel(
            Text(log_message, style="bright_black", no_wrap=True),
            title="LOGS",
            border_style="bold blue",
            height=height,
        )

    def create_data_preview_panel(self, data_before_transformation: dict, data_after_transformation: dict) -> Panel:
        table: Table = Table(
            show_header=True,
            header_style="",
            border_style="bright_black"
        )

        table.add_column("Data Keys (Before)")
        table.add_column("Data Values (Before)")
        table.add_column("Data Keys (After)")
        table.add_column("Data Values (After)")

        keys_before_transformation: list = list(data_before_transformation.keys())
        keys_after_transformation: list = list(data_after_transformation.keys())
        used_keys_after_transformation: set = set()

        for key in keys_before_transformation:
            matching_key: str | None = self.find_matching_key_after_transform(key, keys_after_transformation)

            value_before_transformation: str = data_before_transformation.get(key) if key else ""
            value_after_transformation: str = data_after_transformation.get(matching_key) if matching_key else ""

            used_keys_after_transformation.add(matching_key)

            key_style: str = "bold green" if matching_key and key != matching_key else ""
            value_style: str = "bold green" if str(value_before_transformation) != str(value_after_transformation) else "bright_black"

            table.add_row(
                Text(str(key), style="bright_black"),
                Text(str(value_before_transformation), style="bright_black"),
                Text(str(matching_key) if matching_key else "", style=key_style),
                Text(str(value_after_transformation), style=value_style)
            )

        for key in keys_after_transformation:
            if key not in used_keys_after_transformation:
                value_after_transformation: str = data_after_transformation.get(key)
                key_style: str = "bold green"
                value_style: str = "bold green"

                table.add_row(
                    "",
                    "",
                    Text(str(key), style=key_style),
                    Text(str(value_after_transformation), style=value_style)
                )

        return Panel(
            table,
            title="LIVE DATA PREVIEW",
            border_style="bold blue"
        )

    def find_matching_key_after_transform(self, key_before_transformation: str, keys_after_transformation: list) -> Optional[str]:
        for key in keys_after_transformation:
            if key.lower() == key_before_transformation.lower():
                return key

        return None
