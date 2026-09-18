"""Document loader tests using temporary files."""

from pathlib import Path

import pytest

from src.document_loader import load_documents


def test_load_txt_documents(tmp_path: Path) -> None:
    sample = tmp_path / "policy.txt"
    sample.write_text("Waiting period is 90 days.\n\nGrace period is 15 days.", encoding="utf-8")
    loaded = load_documents(tmp_path)
    assert len(loaded) == 1
    assert loaded[0].source == "policy.txt"
    assert loaded[0].file_type == "txt"
    assert len(loaded[0].pages) == 2


def test_missing_folder_raises() -> None:
    with pytest.raises(FileNotFoundError):
        load_documents(Path("definitely_missing_data_dir_xyz"))
