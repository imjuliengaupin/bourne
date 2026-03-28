"""
Introspection mixin providing runtime object inspection capabilities.

This module contains shared introspection functionality that was previously duplicated
across multiple classes, implementing DRY principles for debugging and reflection methods.
"""

import inspect
from types import FrameType
from typing import Optional


class IntrospectionMixin:
    """
    Base utility class providing common methods for logging and debugging.

    This class should be inherited by any class that needs access to common
    utility methods like class labeling and caller method identification.
    """

    def get_class_label(self) -> str:
        """
        Get the class name as a string label.

        Returns:
            The name of the current class
        """

        return type(self).__name__

    def get_caller_method(self) -> str:
        """
        Get the name of the method that called the current method.

        Uses stack frame inspection to determine the calling method name,
        which is useful for logging and debugging purposes.

        Returns:
            The caller method name with parentheses, or `unknown_caller_method()` if not found
        """

        frame: Optional[FrameType] = inspect.currentframe()

        if frame is not None and frame.f_back is not None:
            return frame.f_back.f_code.co_name + "()"

        return "unknown_caller_method()"
