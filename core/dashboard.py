
from typing import Any, Dict, List, Optional, Tuple, Union

from rich.columns import Columns
from rich.console import Console
from rich.panel import Panel
from rich.style import Style
from rich.table import Table
from rich.text import Text

from core.constants import AgentTaskResult
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
        AgentTaskResult.PENDING.value: Style(color="bright_black", bold=True),
        AgentTaskResult.IN_PROGRESS.value: Style(color="blue", bold=True),
        AgentTaskResult.SUCCESS.value: Style(color="green", bold=True),
        AgentTaskResult.SUCCESS_WITH_WARNINGS.value: Style(color="orange3", bold=True),
        AgentTaskResult.FAILED.value: Style(color="red", bold=True),
        AgentTaskResult.RETRIED.value: Style(color="orange3", bold=True),
    }

    def __init__(self, logger: Logger) -> None:
        logger.log("Dashboard", "ℹ️ INFO: Initializing dashboard...")

        self.console: Console = Console()
        self.max_logs: int = logger.max_logs

    def render(self, tasks: List[WorkflowTask], logs: List[str], data_before_transformation: Optional[Dict[str, Any]] = None, data_after_transformation: Optional[Dict[str, Any]] = None) -> Columns:
        panels: List[Union[Table, Panel]] = [self.create_tasks_table(tasks), self.create_logs_panel(logs)]

        if data_before_transformation is not None and data_after_transformation is not None:
            panels.append(self.create_data_preview_panel(data_before_transformation, data_after_transformation))

        return Columns(panels)

    def get_status_style(self, status: Optional[str]) -> Optional[Style]:
        return self.STATUS_STYLES.get(str(status)) if status else None

    def create_tasks_table(self, workflow_tasks: List[WorkflowTask]) -> Table:
        tasks_table: Table = Table(
            show_header=True,
            header_style="bold blue",
            border_style="blue",
        )

        for header, _ in self.COLUMN_DEFINITIONS:
            tasks_table.add_column(header, justify="left", no_wrap=True)

        for task in workflow_tasks:
            row_values: List[Text] = []
            value: str = ""

            for _, key in self.COLUMN_DEFINITIONS:
                if key == "task_name":
                    value = str(task.get("task_name"))
                elif key == "agent_name":
                    value = str(task.get("agent_name"))
                elif key == "agent_method_name":
                    value = str(task.get("agent_method_name"))
                elif key == "task_status":
                    value = str(task.get("task_status"))
                elif key == "retries_left":
                    value = str(task.get("retries_left"))
                else:
                    value = ""

                if key == "task_status":
                    style: Optional[Style] = self.get_status_style(task.get("task_status"))
                    row_values.append(Text(value, style=style if style else Style()))
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

    def create_data_preview_panel(self, data_before_transformation: Dict[str, Any], data_after_transformation: Dict[str, Any]) -> Panel:
        table: Table = Table(
            show_header=True,
            header_style="",
            border_style="bright_black"
        )

        table.add_column("Data Keys (Before)")
        table.add_column("Data Values (Before)")
        table.add_column("Data Keys (After)")
        table.add_column("Data Values (After)")

        # New logic starts here
        all_changes = self.detect_data_changes(data_before_transformation, data_after_transformation)

        self.add_data_changes_to_table(table, all_changes)

        return Panel(
            table,
            title="LIVE DATA PREVIEW",
            border_style="bold blue"
        )

    def detect_data_changes(self, before: Dict[str, Any], after: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Detect all data changes including nested arrays and objects"""
        changes = []

        # Track all keys from both datasets
        all_keys_before = set(before.keys())
        all_keys_after = set(after.keys())

        # Process each key from before data
        for key_before in all_keys_before:
            matching_key_after = self.find_matching_key_after_transform(key_before, list(all_keys_after))

            if matching_key_after:
                all_keys_after.remove(matching_key_after)  # Mark as processed

            value_before = before[key_before]
            value_after = after[matching_key_after] if matching_key_after else None

            # Check if this is an array of objects that needs nested analysis
            if isinstance(value_before, list) and isinstance(value_after, list):
                nested_changes = self.detect_nested_data_changes(key_before, matching_key_after, value_before, value_after)
                changes.extend(nested_changes)
            else:
                # Regular key-value pair
                changes.append({
                    'path': '',
                    'key_before': key_before,
                    'key_after': matching_key_after or '',
                    'value_before': str(value_before),
                    'value_after': str(value_after) if value_after is not None else '',
                    'key_changed': key_before != matching_key_after if matching_key_after else True,
                    'value_changed': str(value_before) != str(value_after) if value_after is not None else True
                })

        # Add any remaining keys that only exist in after data
        for remaining_key in all_keys_after:
            changes.append({
                'path': '',
                'key_before': '',
                'key_after': remaining_key,
                'value_before': '',
                'value_after': str(after[remaining_key]),
                'key_changed': True,
                'value_changed': True
            })

        return changes

    def detect_nested_data_changes(self, key_before: str, key_after: Optional[str], array_before: List[Any], array_after: List[Any]) -> List[Dict[str, Any]]:
        """Detect changes within arrays, especially arrays of objects"""
        changes = []

        # First, add the top-level array key change
        changes.append({
            'path': '',
            'key_before': key_before,
            'key_after': key_after or '',
            'value_before': f"Array[{len(array_before)}]",
            'value_after': f"Array[{len(array_after)}]" if key_after else '',
            'key_changed': key_before != key_after if key_after else True,
            'value_changed': False  # Array length comparison
        })

        # Then, analyze objects within the arrays
        for i, (item_before, item_after) in enumerate(zip(array_before, array_after)):
            if isinstance(item_before, dict) and isinstance(item_after, dict):
                # CRITICAL: Detect changes within array objects
                for obj_key_before in item_before.keys():
                    matching_obj_key_after = self.find_matching_key_after_transform(obj_key_before, list(item_after.keys()))

                    if matching_obj_key_after:
                        obj_value_before = str(item_before[obj_key_before])
                        obj_value_after = str(item_after[matching_obj_key_after])

                        changes.append({
                            'path': f'[{i}]',
                            'key_before': obj_key_before,
                            'key_after': matching_obj_key_after,
                            'value_before': obj_value_before,
                            'value_after': obj_value_after,
                            'key_changed': obj_key_before != matching_obj_key_after,
                            'value_changed': obj_value_before != obj_value_after
                        })

        return changes

    def add_data_changes_to_table(self, table: Table, changes: List[Dict[str, Any]]) -> None:
        """Add all detected changes to the table with appropriate highlighting"""

        for change in changes:
            # Determine styling based on what changed
            key_style = "bold green" if change['key_changed'] else "bright_black"
            value_style = "bold green" if change['value_changed'] else "bright_black"

            # Format path for nested items
            path_prefix = f"{change['path']}." if change['path'] else ""
            key_before_display = f"{path_prefix}{change['key_before']}" if change['key_before'] else ""
            key_after_display = f"{path_prefix}{change['key_after']}" if change['key_after'] else ""

            table.add_row(
                Text(key_before_display, style="bright_black"),
                Text(change['value_before'], style="bright_black"),
                Text(key_after_display, style=key_style),
                Text(change['value_after'], style=value_style)
            )

    def find_matching_key_after_transform(self, key_before_transformation: str, keys_after_transformation: List[str]) -> Optional[str]:
        for key in keys_after_transformation:
            if key.lower() == key_before_transformation.lower():
                return key

        return None
