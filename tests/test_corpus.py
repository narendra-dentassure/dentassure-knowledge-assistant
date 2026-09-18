"""Corpus checks — sample folder must include PDF, DOCX, and TXT."""

from src.config import PROJECT_ROOT


def test_sample_docs_cover_required_formats() -> None:
    folder = PROJECT_ROOT / "data" / "sample_docs"
    names = {path.name for path in folder.iterdir() if path.is_file()}
    assert any(name.endswith(".pdf") for name in names)
    assert any(name.endswith(".docx") for name in names)
    assert any(name.endswith(".txt") for name in names)
    assert "dentassure_policy_guide.pdf" in names
    assert "dentassure_clinic_front_desk_sop.docx" in names
    assert "dentassure_member_faq.txt" in names
