from pathlib import Path

import pytest

from app.storage import LocalObjectStorage
from app.sources.service import safe_filename


def test_local_storage_round_trip_and_delete(tmp_path: Path) -> None:
    storage = LocalObjectStorage(tmp_path)
    stored = storage.put("users/u1/source.docx", b"document")

    assert stored.size == 8
    assert storage.get(stored.key) == b"document"
    storage.delete(stored.key)
    assert not (tmp_path / "users/u1/source.docx").exists()


@pytest.mark.parametrize(
    "key",
    ["../secret", "/absolute", "folder/../secret", "folder\\..\\secret", "C:/secret"],
)
def test_local_storage_rejects_unsafe_keys(tmp_path: Path, key: str) -> None:
    storage = LocalObjectStorage(tmp_path)
    with pytest.raises(ValueError):
        storage.put(key, b"nope")


def test_uploaded_filename_is_reduced_to_safe_basename() -> None:
    assert safe_filename("../../Quarterly brief (final).docx") == "Quarterly_brief_final_.docx"
    assert safe_filename("..\\..\\report.pptx") == "report.pptx"
