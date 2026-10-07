from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .applicability import DeploymentContext, ValidatedScope
from .finalization import FrozenFinalizer
from .qualification import QualificationEvidence
from .records import ForecastRecord


def load_scenario(path: str | Path) -> dict[str, Any]:
    p = Path(path)
    return json.loads(p.read_text(encoding="utf-8"))


def scenario_objects(d: dict[str, Any]):
    candidates = [ForecastRecord.from_dict(x) for x in d["candidates"]]
    qualification = QualificationEvidence(**d["qualification"])
    scope = ValidatedScope(**d["validated_scope"])
    deployment = DeploymentContext(**d["deployment_context"])
    finalizer = None
    if d.get("finalizer_record"):
        finalizer = FrozenFinalizer(ForecastRecord.from_dict(d["finalizer_record"]))
    return candidates, qualification, scope, deployment, finalizer
