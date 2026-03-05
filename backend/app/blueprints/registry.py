from __future__ import annotations

from typing import Any, Dict, List

from app.blueprints.frylow_blueprint import get_all_blueprints as _get_all_blueprints
from app.blueprints.frylow_blueprint import get_blueprint_json as _get_blueprint_json


def get_all_blueprints() -> List[Dict[str, Any]]:
    return _get_all_blueprints()


def get_blueprint_json(slug: str) -> Dict[str, Any]:
    return _get_blueprint_json(slug)
