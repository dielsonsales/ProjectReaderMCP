import os

import pytest

import utils.text_edit_utils as text_edit_utils
from utils.text_edit_utils import insert_text, replace_text


def test_replace_text_changes_one_unique_match(tmp_path):
    file_path = tmp_path / "sample.txt"
    file_path.write_bytes(b"before\nneedle\nafter\n")

    result = replace_text(file_path, "needle", "changed")

    assert result["success"] is True
    assert "-needle\n" in result["diff"]
    assert file_path.read_bytes() == b"before\nchanged\nafter\n"


def test_replace_text_can_remove_a_complete_line(tmp_path):
    file_path = tmp_path / "sample.txt"
    file_path.write_bytes(b"first\nremove me\nlast\n")

    result = replace_text(file_path, "remove me\n", "")

    assert result["success"] is True
    assert file_path.read_bytes() == b"first\nlast\n"


@pytest.mark.parametrize(
    ("position", "expected"),
    [("before", b"start anchor"), ("after", b"anchor end")],
)
def test_insert_text_respects_position(tmp_path, position, expected):
    file_path = tmp_path / "sample.txt"
    file_path.write_bytes(b"anchor")
    text = "start " if position == "before" else " end"

    result = insert_text(file_path, "anchor", text, position)

    assert result["success"] is True
    assert file_path.read_bytes() == expected


@pytest.mark.parametrize(
    ("content", "search_text", "expected_count"),
    [(b"present", "missing", 0), (b"aaaa", "aaa", 2)],
)
def test_replace_text_rejects_missing_or_ambiguous_matches(
    tmp_path, content, search_text, expected_count
):
    file_path = tmp_path / "sample.txt"
    file_path.write_bytes(content)

    result = replace_text(file_path, search_text, "changed")

    assert result["success"] is False
    assert result["match_count"] == expected_count
    assert file_path.read_bytes() == content


def test_replace_text_rejects_empty_search_text(tmp_path):
    file_path = tmp_path / "sample.txt"
    file_path.write_bytes(b"unchanged")

    result = replace_text(file_path, "", "changed")

    assert result["success"] is False
    assert file_path.read_bytes() == b"unchanged"


@pytest.mark.parametrize("position", ["before", "after"])
def test_insert_text_dry_run_does_not_change_file_or_metadata(tmp_path, position):
    file_path = tmp_path / "sample.txt"
    file_path.write_bytes(b"anchor\n")
    original_content = file_path.read_bytes()
    original_stat = file_path.stat()

    result = insert_text(file_path, "anchor", "addition\n", position, dry_run=True)

    assert result["success"] is True
    assert result["dry_run"] is True
    assert result["diff"].startswith("--- a/sample.txt\n+++ b/sample.txt\n")
    assert file_path.read_bytes() == original_content
    assert file_path.stat().st_mtime_ns == original_stat.st_mtime_ns


@pytest.mark.parametrize(
    ("content", "expected"),
    [
        (b"first\nneedle\nlast\n", b"first\nchanged\nlast\n"),
        (b"first\r\nneedle\r\nlast\r\n", b"first\r\nchanged\r\nlast\r\n"),
        (b"first\nneedle\nlast", b"first\nchanged\nlast"),
    ],
)
def test_replace_text_preserves_newline_style_and_final_newline(
    tmp_path, content, expected
):
    file_path = tmp_path / "sample.txt"
    file_path.write_bytes(content)

    result = replace_text(file_path, "needle", "changed")

    assert result["success"] is True
    assert file_path.read_bytes() == expected


def test_replace_text_rejects_mixed_newlines(tmp_path):
    file_path = tmp_path / "sample.txt"
    file_path.write_bytes(b"first\r\nneedle\nlast\r\n")

    result = replace_text(file_path, "needle", "changed")

    assert result["success"] is False
    assert "mixed or unsupported newline" in result["error"]
    assert file_path.read_bytes() == b"first\r\nneedle\nlast\r\n"


def test_replace_text_rejects_invalid_utf8(tmp_path):
    file_path = tmp_path / "sample.txt"
    file_path.write_bytes(b"needle\xff")

    result = replace_text(file_path, "needle", "changed")

    assert result["success"] is False
    assert file_path.read_bytes() == b"needle\xff"


def test_replace_text_leaves_original_when_atomic_replace_fails(tmp_path, monkeypatch):
    file_path = tmp_path / "sample.txt"
    file_path.write_bytes(b"before needle after")

    def fail_replace(source, destination):
        raise OSError("simulated replace failure")

    monkeypatch.setattr(text_edit_utils.os, "replace", fail_replace)

    result = replace_text(file_path, "needle", "changed")

    assert result["success"] is False
    assert "simulated replace failure" in result["error"]
    assert file_path.read_bytes() == b"before needle after"
    assert list(tmp_path.glob(".sample.txt.*.tmp")) == []


def test_insert_text_rejects_invalid_position_and_empty_file_anchor(tmp_path):
    file_path = tmp_path / "sample.txt"
    file_path.write_bytes(b"")

    invalid_position = insert_text(file_path, "anchor", "text", "beside")
    empty_file = insert_text(file_path, "anchor", "text")

    assert invalid_position["success"] is False
    assert empty_file["success"] is False
    assert file_path.read_bytes() == b""