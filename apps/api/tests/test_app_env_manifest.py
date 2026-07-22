"""Validate infra/deploy/app-env.manifest.json shape (names only, no secrets)."""

from __future__ import annotations

import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
MANIFEST = REPO_ROOT / "infra" / "deploy" / "app-env.manifest.json"


def test_app_env_manifest_shape():
    assert MANIFEST.is_file(), f"missing {MANIFEST}"
    data = json.loads(MANIFEST.read_text(encoding="utf-8"))
    assert set(data.keys()) == {"api", "web"}
    assert isinstance(data["api"], list) and isinstance(data["web"], list)
    for section in ("api", "web"):
        for name in data[section]:
            assert isinstance(name, str) and name
            assert "=" not in name, f"manifest must list names only, got {name!r}"
            assert not name.startswith("http"), f"looks like a value, not a name: {name!r}"
            # Reject obvious secret material
            assert "://" not in name
            assert len(name) < 128
