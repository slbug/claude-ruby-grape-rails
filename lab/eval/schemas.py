"""Shared dataclasses for deterministic eval results."""

from __future__ import annotations

from dataclasses import dataclass, field
import json
from pathlib import Path
from typing import Any


@dataclass
class EvalCheck:
    check_type: str
    description: str
    params: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> "EvalCheck":
        data = dict(raw)
        check_type = data.pop("type", data.pop("check_type", ""))
        description = data.pop("desc", data.pop("description", ""))
        return cls(check_type=check_type, description=description, params=data)


@dataclass
class EvalDimension:
    name: str
    weight: float
    checks: list[EvalCheck]

    @classmethod
    def from_dict(cls, name: str, raw: dict[str, Any]) -> "EvalDimension":
        checks = [EvalCheck.from_dict(item) for item in raw.get("checks", [])]
        return cls(name=name, weight=float(raw.get("weight", 0.0)), checks=checks)


@dataclass
class EvalDefinition:
    subject: str
    subject_path: str
    dimensions: dict[str, EvalDimension]

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> "EvalDefinition":
        subject = raw.get("skill", raw.get("agent", raw.get("subject", "")))
        subject_path = raw.get("skill_path", raw.get("agent_path", raw.get("subject_path", "")))
        dimensions = {
            name: EvalDimension.from_dict(name, value)
            for name, value in raw.get("dimensions", {}).items()
        }
        return cls(subject=subject, subject_path=subject_path, dimensions=dimensions)

    @classmethod
    def from_file(cls, path: str | Path) -> "EvalDefinition":
        return cls.from_dict(json.loads(Path(path).read_text(encoding="utf-8")))


@dataclass
class AssertionResult:
    check_type: str
    description: str
    passed: bool
    evidence: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "type": self.check_type,
            "desc": self.description,
            "passed": self.passed,
            "evidence": self.evidence,
        }


@dataclass
class DimensionResult:
    name: str
    score: float
    assertions: list[AssertionResult]

    def to_dict(self) -> dict[str, Any]:
        return {
            "score": round(self.score, 4),
            "assertions": [item.to_dict() for item in self.assertions],
        }


@dataclass
class SubjectScore:
    subject_name: str
    subject_path: str
    composite: float
    dimensions: dict[str, DimensionResult]

    def to_dict(self) -> dict[str, Any]:
        return {
            "subject": self.subject_name,
            "path": self.subject_path,
            "composite": round(self.composite, 4),
            "dimensions": {name: item.to_dict() for name, item in self.dimensions.items()},
        }
