"""Cross-platform operator password input preserves the credential, not line endings."""

import io

import pytest

from app.scripts import create_super_admin


@pytest.mark.unit
def test_stdin_password_strips_crlf(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(create_super_admin.sys, "stdin", io.StringIO("FixturePassword123\r\n"))
    assert create_super_admin._password_from_operator(True) == "FixturePassword123"
