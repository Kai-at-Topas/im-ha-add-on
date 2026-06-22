"""Add-on configuration persistence.

ConfigModel (Pydantic v2) defines the on-disk JSON schema and validates
all values. ConfigManager reads and writes /data/options.json (production)
or ./data/options.json (local dev fallback).

Partial updates:
    POST /api/config sends only changed fields. update_config() in main.py
    reads the current file, merges the incoming dict, validates the result,
    then writes — absent fields are preserved rather than reset to defaults.

Unknown-key filtering:
    _model_from_data() strips unrecognised keys before constructing the
    model. This lets old config files (e.g. containing a removed field)
    load cleanly. The strict extra="forbid" rule still applies to API
    writes, where unexpected keys signal a real client error.
"""

import json
import os
from pathlib import Path
from typing import Optional

from fastapi import HTTPException
from pydantic import BaseModel, ConfigDict, Field, field_validator


class ConfigModel(BaseModel):
    """Schema for the add-on's persisted configuration.

    All entity fields are validated to be in 'domain.name' format.
    MQTT fields are only used when mqtt_opt_in is True.
    """

    model_config = ConfigDict(extra="forbid")

    weather_entity: Optional[str] = Field(default=None)
    power_entity: Optional[str] = Field(default=None)
    energy_entity: Optional[str] = Field(default=None)
    mqtt_opt_in: bool = Field(default=False)
    cost_per_kwh: Optional[float] = Field(default=None)
    annual_basic_price: Optional[float] = Field(default=None)
    mqtt_host: Optional[str] = Field(default=None)
    mqtt_port: Optional[int] = Field(default=None)
    mqtt_user: Optional[str] = Field(default=None)
    mqtt_password: Optional[str] = Field(default=None)
    mqtt_topic: Optional[str] = Field(default=None)

    @field_validator("weather_entity", "power_entity", "energy_entity")
    @classmethod
    def validate_ha_entity(cls, v: Optional[str]) -> Optional[str]:
        """Ensure entity IDs follow the 'domain.name' convention."""
        if not v:  # None or empty string → store as None
            return None
        if "." not in v or len(v.split(".")) != 2:
            raise ValueError("Entity must be in 'domain.name' format")
        return v


class ConfigManager:
    """Reads and writes the add-on config file with graceful fallbacks."""

    def __init__(self, config_path: str = "/data/options.json"):
        self.config_path = Path(config_path)
        self.fallback_path = Path("./data/options.json")

    def read_config(self) -> ConfigModel:
        """Read configuration from file, falling back to defaults on error.

        Tries config_path first, then fallback_path, then returns a default
        ConfigModel if neither file exists. JSON decode errors and missing
        files are caught and logged rather than raised.
        """
        try:
            if self.config_path.exists():
                with open(self.config_path, "r") as f:
                    return self._model_from_data(json.load(f))

            if self.fallback_path.exists():
                with open(self.fallback_path, "r") as f:
                    return self._model_from_data(json.load(f))

            return ConfigModel()

        except (json.JSONDecodeError, FileNotFoundError) as e:
            print(f"[CONFIG] Error reading config: {e}")
            return ConfigModel()

    @staticmethod
    def _model_from_data(config_data: dict) -> ConfigModel:
        """Build a ConfigModel, silently dropping unknown/legacy keys."""
        known = set(ConfigModel.model_fields)
        dropped = set(config_data) - known
        if dropped:
            print(
                f"[CONFIG] Ignoring unknown config keys: {sorted(dropped)}"
            )
        filtered = {k: v for k, v in config_data.items() if k in known}
        return ConfigModel(**filtered)

    def write_config(self, config: ConfigModel) -> None:
        """Persist config to disk, creating parent directories as needed."""
        try:
            Path(self.config_path).parent.mkdir(parents=True, exist_ok=True)
            with open(self.config_path, "w") as f:
                json.dump(config.model_dump(), f, indent=2)
            print(
                f"[CONFIG] Updated configuration: "
                f"{config.model_dump_json()}"
            )
        except Exception as e:
            print(f"[CONFIG] Error writing config: {e}")
            raise HTTPException(
                status_code=500, detail="Failed to save configuration"
            )


# Module-level singleton — imported by main.py and ha_proxy.py.
config_manager = ConfigManager(
    config_path=os.getenv("CONFIG_PATH", "/data/options.json")
)
