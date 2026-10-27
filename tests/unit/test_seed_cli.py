import os
import subprocess
from pathlib import Path


def test_demo_module_rejects_remote_host_before_database_access() -> None:
    env = os.environ.copy()
    env.pop("PYTHONPATH", None)
    env.update(
        DATABASE_URL="postgresql+psycopg://demo:demo@remote.invalid/demo",
        API_KEY="synthetic-demo-key",
    )
    result = subprocess.run(
        ["uv", "run", "python", "-m", "scripts.seed_demo", "--yes"],
        cwd=Path(__file__).resolve().parents[2],
        env=env,
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode != 0
    assert "no parece ser local" in result.stderr
    assert "ModuleNotFoundError" not in result.stderr


def test_official_demo_command_is_documented() -> None:
    from scripts import seed_demo

    assert "uv run python -m scripts.seed_demo" in seed_demo.__doc__
    source = Path("dashboard/app.py").read_text(encoding="utf-8")
    assert "uv run python -m scripts.seed_demo" in source
