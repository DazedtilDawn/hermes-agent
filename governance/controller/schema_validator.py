from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .config import GovernanceConfig, build_config


class SchemaValidationError(ValueError):
    pass


class SchemaValidator:
    def __init__(self, config: GovernanceConfig | None = None):
        self.config = config or build_config()
        self.schema_paths = {
            "incident_report": self.config.schema_dir / "incident_report.schema.json",
            "verification_report": self.config.schema_dir / "verification_report.schema.json",
            "approval_report": self.config.schema_dir / "approval_report.schema.json",
            "execution_report": self.config.schema_dir / "execution_report.schema.json",
            "governance_incident": self.config.schema_dir / "governance_incident.schema.json",
        }

    def load_schema(self, artifact_type: str) -> dict[str, Any]:
        try:
            path = self.schema_paths[artifact_type]
        except KeyError as exc:
            raise SchemaValidationError(f"Unknown artifact type: {artifact_type}") from exc
        return json.loads(path.read_text(encoding="utf-8"))

    def validate(self, artifact_type: str, payload: dict[str, Any]) -> None:
        schema = self.load_schema(artifact_type)
        self._validate_node(payload, schema, "$")

    def validate_file(self, path: Path) -> None:
        payload = json.loads(path.read_text(encoding="utf-8"))
        artifact_type = payload.get("artifact_type")
        if not artifact_type:
            raise SchemaValidationError("artifact_type is required")
        self.validate(artifact_type, payload)

    def _validate_node(self, value: Any, schema: dict[str, Any], pointer: str) -> None:
        if "const" in schema and value != schema["const"]:
            raise SchemaValidationError(f"{pointer}: expected const {schema['const']!r}, got {value!r}")

        expected_type = schema.get("type")
        if isinstance(expected_type, list):
            if not any(self._matches_type(value, entry) for entry in expected_type):
                raise SchemaValidationError(f"{pointer}: expected one of types {expected_type}, got {type(value).__name__}")
        elif expected_type and not self._matches_type(value, expected_type):
            raise SchemaValidationError(f"{pointer}: expected type {expected_type}, got {type(value).__name__}")

        if "enum" in schema and value not in schema["enum"]:
            raise SchemaValidationError(f"{pointer}: expected one of {schema['enum']}, got {value!r}")

        if value is None:
            return

        if expected_type == "object" or (isinstance(expected_type, list) and isinstance(value, dict)):
            required = schema.get("required", [])
            for key in required:
                if key not in value:
                    raise SchemaValidationError(f"{pointer}: missing required property {key!r}")
            properties = schema.get("properties", {})
            additional = schema.get("additionalProperties", True)
            if additional is False:
                extras = set(value) - set(properties)
                if extras:
                    raise SchemaValidationError(f"{pointer}: unexpected properties {sorted(extras)!r}")
            for key, child_schema in properties.items():
                if key in value:
                    self._validate_node(value[key], child_schema, f"{pointer}.{key}")

        if expected_type == "array" or (isinstance(expected_type, list) and isinstance(value, list)):
            item_schema = schema.get("items")
            if item_schema:
                for index, item in enumerate(value):
                    self._validate_node(item, item_schema, f"{pointer}[{index}]")

    @staticmethod
    def _matches_type(value: Any, expected: str) -> bool:
        if expected == "object":
            return isinstance(value, dict)
        if expected == "array":
            return isinstance(value, list)
        if expected == "string":
            return isinstance(value, str)
        if expected == "boolean":
            return isinstance(value, bool)
        if expected == "integer":
            return isinstance(value, int) and not isinstance(value, bool)
        if expected == "number":
            return isinstance(value, (int, float)) and not isinstance(value, bool)
        if expected == "null":
            return value is None
        return True
