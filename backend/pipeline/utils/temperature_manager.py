"""Utility for managing stage-specific temperatures."""

from typing import Dict
from pathlib import Path
import yaml


class TemperatureManager:
    """Manages temperature settings for each pipeline stage."""

    def __init__(self, config_path: str = "config/models.yaml"):
        with open(config_path, "r") as f:
            config = yaml.safe_load(f)

        self.temperatures = config.get("temperatures", {})

    def get_temperature(self, stage_name: str) -> float:
        """Get temperature for a specific stage."""
        return self.temperatures.get(stage_name, 0.7)

    def get_all_temperatures(self) -> Dict[str, float]:
        """Get all configured temperatures."""
        return self.temperatures
