import json
import re
from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app
from app.version import __version__

ROOT = Path(__file__).resolve().parents[2]


def test_version_is_semver_and_matches_web_package() -> None:
    assert re.fullmatch(r"\d+\.\d+\.\d+", __version__)
    package = json.loads((ROOT / "web" / "package.json").read_text(encoding="utf-8"))
    assert package["version"] == __version__


def test_changelog_has_entry_for_current_version() -> None:
    changelog = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    assert re.search(rf"^## \[{re.escape(__version__)}\] - \d{{4}}-\d{{2}}-\d{{2}}$", changelog, re.MULTILINE)


def test_health_reports_version() -> None:
    assert TestClient(app).get("/api/health").json() == {"status": "ok", "version": __version__}
