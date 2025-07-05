
from typing import Dict, List, Optional, Tuple

from rich.columns import Columns
from rich.console import Console
from rich.panel import Panel
from rich.style import Style
from rich.table import Table
from rich.text import Text

from core import constants
from core.workflow.workflow_task import WorkflowTask


class Dashboard:

    COLUMN_DEFINITIONS: List[Tuple[str, str]] = [
        ("TASK NAME", constants.TASK_NAME),
        ("AGENT", constants.AGENT_NAME),
        ("METHOD TO RUN", constants.AGENT_METHOD_NAME),
        ("STATUS", constants.TASK_STATUS),
        ("RETRIES LEFT", constants.RETRIES_LEFT),
    ]

    DEFAULT_STYLE: Style = Style(color="bright_black")

    STATUS_STYLES: Dict[str, Style] = {
        constants.STATUS_SUCCESS: Style(color="green", bold=True),
        constants.STATUS_IN_PROGRESS: Style(color="blue", bold=True),
        constants.STATUS_FAILED: Style(color="red", bold=True),
        constants.STATUS_RETRIED: Style(color="orange3", bold=True),
        constants.STATUS_PENDING: Style(color="bright_black", bold=True),
    }

    def __init__(self, max_logs: int) -> None:
        self.console: Console = Console()
        self.max_logs: int = max_logs

    def render(self, tasks: List[WorkflowTask], logs: List[str], data_before_transform: Optional[dict] = None, data_after_transform: Optional[dict] = None) -> Columns:
        panels: list = [self.create_tasks_table(tasks), self.create_logs_panel(logs)]

        if data_before_transform is not None and data_after_transform is not None:
            panels.append(self.create_data_preview_panel(data_before_transform, data_after_transform))

        return Columns(panels)

    def create_data_preview_panel(self, data_before_transform: dict, data_after_transform: dict) -> Panel:
        table: Table = Table(
            show_header=True,
            header_style="",
            border_style="bright_black"
        )

        table.add_column("Data Keys (Before)")
        table.add_column("Data Values (Before)")
        table.add_column("Data Keys (After)")
        table.add_column("Data Values (After)")

        before_keys: list = list(data_before_transform.keys())
        after_keys: list = list(data_after_transform.keys())
        used_after_keys: set = set()

        for before_key in before_keys:
            after_key: str | None = self.match_after_key(before_key, after_keys)

            before_value: str = data_before_transform.get(before_key, "") if before_key else ""
            after_value: str = data_after_transform.get(after_key, "") if after_key else ""

            used_after_keys.add(after_key)

            key_after_style: str = "bold green" if after_key and before_key != after_key else ""
            value_after_style: str = "bold green" if str(before_value) != str(after_value) else "bright_black"

            table.add_row(
                Text(str(before_key), style="bright_black"),
                Text(str(before_value), style="bright_black"),
                Text(str(after_key) if after_key else "", style=key_after_style),
                Text(str(after_value), style=value_after_style)
            )

        for after_key in after_keys:
            if after_key not in used_after_keys:
                after_value: str = data_after_transform.get(after_key, "")

                table.add_row(
                    "",
                    "",
                    Text(str(after_key), style="bold green"),
                    Text(str(after_value), style="bold green")
                )

        return Panel(
            table,
            title="LIVE DATA PREVIEW",
            border_style="bold blue"
        )

    def match_after_key(self, before_key: str, after_keys: list) -> Optional[str]:
        for key in after_keys:
            if key.lower() == before_key.lower():
                return key

        return None

    def get_status_style(self, status: Optional[str]) -> Style:
        return self.STATUS_STYLES.get(str(status), self.DEFAULT_STYLE)

    def create_tasks_table(self, tasks: List[WorkflowTask]) -> Table:
        tasks_table: Table = Table(
            show_header=True,
            header_style="bold blue",
            border_style="blue",
        )

        for header, _ in self.COLUMN_DEFINITIONS:
            tasks_table.add_column(header, justify="left", no_wrap=True)

        for task in tasks:
            row_values: list = []

            for _, key in self.COLUMN_DEFINITIONS:
                value: str = str(task.get(key))

                if key == constants.TASK_STATUS:
                    style: Style = self.get_status_style(value)
                    row_values.append(Text(value, style=style))
                else:
                    row_values.append(Text(value))

            tasks_table.add_row(*row_values)

        return tasks_table

    def create_logs_panel(self, logs: List[str]) -> Panel:
        log_message: str = "\n".join(logs) if logs else "ℹ️ INFO: Initializing dashboard..."

        # Define a fixed height for the panel to match the max_logs setting, +2 for top/bottom borders
        height: int = self.max_logs + 2

        return Panel(
            Text(log_message, style=self.DEFAULT_STYLE, no_wrap=True),
            title="LOGS",
            border_style="bold blue",
            height=height,
        )
