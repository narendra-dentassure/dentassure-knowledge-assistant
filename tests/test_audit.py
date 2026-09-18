"""Audit log tests — write to a temp file, never the real logs folder."""

from src.observability import audit


def test_write_and_read_audit_without_secrets(tmp_path, monkeypatch) -> None:
    path = tmp_path / "audit.jsonl"
    monkeypatch.setattr(audit, "AUDIT_PATH", path)
    audit.write_audit({"question": "grace period?", "role": "Visitor", "grounded": True})
    rows = audit.read_audit(10)
    assert len(rows) == 1
    assert rows[0]["question"] == "grace period?"
    assert rows[0]["role"] == "Visitor"
    assert "api_key" not in rows[0]
    assert path.read_text(encoding="utf-8").count("\n") == 1
