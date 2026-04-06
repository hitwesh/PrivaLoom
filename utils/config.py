"""
Environment-based configuration management for PrivaLoom.

Provides centralized configuration loading from environment variables with
type validation and default values. Maintains backward compatibility with
existing environment helper functions.
"""

import os
from typing import TypeVar

T = TypeVar('T')


class Config:
    """Environment-based configuration manager with type validation."""

    def get_bool(self, name: str, default: bool = False) -> bool:
        """
        Get boolean environment variable.

        Args:
            name: Environment variable name
            default: Default value if variable is not set or invalid

        Returns:
            Boolean value from environment or default
        """
        value = os.getenv(name)
        if value is None:
            return default

        # Handle common boolean representations
        value_lower = value.lower()
        if value_lower in ('true', '1', 'yes', 'on'):
            return True
        elif value_lower in ('false', '0', 'no', 'off'):
            return False
        else:
            # Invalid value, return default
            return default

    def get_float(self, name: str, default: float = 0.0) -> float:
        """
        Get float environment variable.

        Args:
            name: Environment variable name
            default: Default value if variable is not set or invalid

        Returns:
            Float value from environment or default
        """
        value = os.getenv(name)
        if value is None:
            return default

        try:
            return float(value)
        except ValueError:
            return default

    def get_int(self, name: str, default: int = 0) -> int:
        """
        Get integer environment variable.

        Args:
            name: Environment variable name
            default: Default value if variable is not set or invalid

        Returns:
            Integer value from environment or default
        """
        value = os.getenv(name)
        if value is None:
            return default

        try:
            return int(value)
        except ValueError:
            return default

    def get_str(self, name: str, default: str = "") -> str:
        """
        Get string environment variable.

        Args:
            name: Environment variable name
            default: Default value if variable is not set

        Returns:
            String value from environment or default
        """
        return os.getenv(name, default)


# Global configuration instance
config = Config()


# Legacy function aliases for backward compatibility
def _get_env_bool(name: str, default: bool) -> bool:
    """Legacy compatibility function. Use config.get_bool() instead."""
    return config.get_bool(name, default)


def _get_env_float(name: str, default: float) -> float:
    """Legacy compatibility function. Use config.get_float() instead."""
    return config.get_float(name, default)


def _get_env_int(name: str, default: int) -> int:
    """Legacy compatibility function. Use config.get_int() instead."""
    return config.get_int(name, default)