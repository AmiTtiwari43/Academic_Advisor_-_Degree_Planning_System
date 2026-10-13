import subprocess
import sys
from pathlib import Path


def test_production_deploy_check():
    """
    Verify that manage.py check --deploy --settings=config.settings.production runs with zero issues.
    """
    project_root = Path(__file__).resolve().parent.parent
    python_exe = sys.executable

    result = subprocess.run(
        [
            python_exe,
            "manage.py",
            "check",
            "--deploy",
            "--settings=config.settings.production",
        ],
        cwd=project_root,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, f"Check deploy failed: {result.stderr or result.stdout}"
    assert "System check identified no issues" in result.stdout or "0 silenced" in result.stdout


def test_no_hardcoded_secret_keys():
    """
    Verify that no SECRET_KEY string literals are committed in Python source files.
    """
    project_root = Path(__file__).resolve().parent.parent
    py_files = list(project_root.glob("**/*.py"))

    for py_file in py_files:
        if ".venv" in str(py_file) or "node_modules" in str(py_file):
            continue
        content = py_file.read_text(encoding="utf-8")
        for line in content.splitlines():
            line_stripped = line.strip()
            # Flag any line assigning SECRET_KEY = "..." or '...'
            if line_stripped.startswith('SECRET_KEY = "') or line_stripped.startswith(
                "SECRET_KEY = '"
            ):
                raise AssertionError(f"Hardcoded secret key found in {py_file}: {line_stripped}")
