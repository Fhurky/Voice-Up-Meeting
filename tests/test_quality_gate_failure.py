"""The real shell gate must not report a database creation failure as a pass."""

import shutil
import subprocess
from pathlib import Path

import pytest


def test_database_create_failure_propagates_from_conditional_function(tmp_path):
    shell = shutil.which("sh")
    git_shell = Path("C:/Program Files/Git/bin/bash.exe")
    if git_shell.exists():
        shell = str(git_shell)
    if shell is None:
        pytest.skip("POSIX shell is required to execute the shell regression")
    source = (Path(__file__).parents[1] / "scripts/quality-gate.sh").read_text()
    run_step = source[source.index("run_step() {") : source.index("validate_configuration() {")]
    create = source[source.index("create_test_database() {") : source.index("drop_test_database() {")]
    script = tmp_path / "failure.sh"
    script.write_text(
        "#!/bin/sh\nset -eu\nproduct_slug=voiceup\ntest_database_active=false\n"
        "python3() { printf '0123456789ab'; }\n"
        "postgres_sql() { echo 'database deliberately unavailable' >&2; return 17; }\n"
        + run_step
        + create
        + "run_step database-test-create create_test_database\n"
        + "echo unexpected-success\n"
    )
    result = subprocess.run([shell, str(script)], capture_output=True, text=True, check=False)
    assert result.returncode == 17
    assert "status=failed exit_code=17" in result.stdout
    assert "status=passed" not in result.stdout
    assert "unexpected-success" not in result.stdout
