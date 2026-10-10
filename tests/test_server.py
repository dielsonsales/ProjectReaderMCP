import pytest
import server
from server import format_timestamp, list_files, read_file, read_lines, recursive_search

def test_format_timestamp_valid():
    from server import format_timestamp
    timestamp = 1700000000.0
    expected_output = "2023-11-14 22:13:20"
    assert format_timestamp(timestamp) == expected_output, "The format_timestamp function did not return the expected output."


def test_filesystem_tools_report_unconfigured_project_root(monkeypatch):
    monkeypatch.setattr(server, "PROJECT_DIR", None)

    assert list_files() == ["Error: PROJECT_DIR is not configured."]
    assert read_file("target.txt") == "Error: PROJECT_DIR is not configured."
    assert read_lines("target.txt", 1, 1) == "Error: PROJECT_DIR is not configured."
    assert recursive_search("needle") == [(0, 0, "Error: PROJECT_DIR is not configured.")]
    assert server.replace_text("target.txt", "old", "new") == {
        "success": False,
        "dry_run": False,
        "error": "PROJECT_DIR is not configured.",
    }
    assert server.insert_text("target.txt", "anchor", "new") == {
        "success": False,
        "dry_run": False,
        "error": "PROJECT_DIR is not configured.",
    }


def test_read_file_rejects_paths_outside_project(tmp_path, monkeypatch):
    project_root = tmp_path / "project"
    project_root.mkdir()
    outside_file = tmp_path / "outside.txt"
    outside_file.write_text("private\n")
    monkeypatch.setattr(server, "PROJECT_DIR", str(project_root))

    result = read_file("../outside.txt")

    assert result.startswith("Error:")
    assert "relative path inside PROJECT_DIR" in result


def test_read_lines_tool_returns_requested_range(tmp_path, monkeypatch):
    project_root = tmp_path / "project"
    nested_dir = project_root / "src"
    nested_dir.mkdir(parents=True)
    target_file = nested_dir / "target.txt"
    target_file.write_bytes(b"first\r\nsecond\nthird")
    monkeypatch.setattr(server, "PROJECT_DIR", str(project_root))

    result = read_lines("src/target.txt", 2, 3)

    assert result == "second\nthird"


def test_read_lines_tool_reports_invalid_range(tmp_path, monkeypatch):
    project_root = tmp_path / "project"
    project_root.mkdir()
    (project_root / "target.txt").write_text("content\n")
    monkeypatch.setattr(server, "PROJECT_DIR", str(project_root))

    result = read_lines("target.txt", 2, 1)

    assert result.startswith("Error:")
    assert "start_line must not exceed end_line" in result


def test_read_lines_tool_reports_missing_file_and_directory(tmp_path, monkeypatch):
    project_root = tmp_path / "project"
    project_root.mkdir()
    (project_root / "directory").mkdir()
    monkeypatch.setattr(server, "PROJECT_DIR", str(project_root))

    missing_result = read_lines("missing.txt", 1, 1)
    directory_result = read_lines("directory", 1, 1)

    assert missing_result.startswith("Error:")
    assert "not found" in missing_result
    assert directory_result.startswith("Error:")
    assert "not a regular file" in directory_result


@pytest.mark.parametrize("filename", ["../outside.txt", "/outside.txt"])
def test_read_lines_tool_rejects_paths_outside_project(
    tmp_path, monkeypatch, filename
):
    project_root = tmp_path / "project"
    project_root.mkdir()
    outside_file = tmp_path / "outside.txt"
    outside_file.write_text("private\n")
    monkeypatch.setattr(server, "PROJECT_DIR", str(project_root))

    result = read_lines(filename, 1, 1)

    assert result.startswith("Error:")
    assert "relative path inside PROJECT_DIR" in result
    assert outside_file.read_text() == "private\n"


def test_read_lines_tool_rejects_symlink_outside_project(tmp_path, monkeypatch):
    project_root = tmp_path / "project"
    project_root.mkdir()
    outside_file = tmp_path / "outside.txt"
    outside_file.write_text("private\n")
    (project_root / "linked.txt").symlink_to(outside_file)
    monkeypatch.setattr(server, "PROJECT_DIR", str(project_root))

    result = read_lines("linked.txt", 1, 1)

    assert result.startswith("Error:")
    assert "resolves outside PROJECT_DIR" in result


def test_replace_text_tool_dry_run_and_apply(tmp_path, monkeypatch):
    project_root = tmp_path / "project"
    project_root.mkdir()
    target_file = project_root / "target.txt"
    target_file.write_bytes(b"before old text after\n")
    monkeypatch.setattr(server, "PROJECT_DIR", str(project_root))

    dry_run_result = server.replace_text("target.txt", "old text", "new text", dry_run=True)

    assert dry_run_result["success"] is True
    assert dry_run_result["dry_run"] is True
    assert "-before old text after\n" in dry_run_result["diff"]
    assert target_file.read_bytes() == b"before old text after\n"

    apply_result = server.replace_text("target.txt", "old text", "new text")

    assert apply_result["success"] is True
    assert apply_result["dry_run"] is False
    assert target_file.read_bytes() == b"before new text after\n"


def test_insert_text_tool_inserts_before_or_after_anchor(tmp_path, monkeypatch):
    project_root = tmp_path / "project"
    project_root.mkdir()
    target_file = project_root / "target.txt"
    target_file.write_bytes(b"anchor")
    monkeypatch.setattr(server, "PROJECT_DIR", str(project_root))

    before_result = server.insert_text("target.txt", "anchor", "before ", "before")

    assert before_result["success"] is True
    assert target_file.read_bytes() == b"before anchor"

    after_result = server.insert_text("target.txt", "anchor", " after", "after")

    assert after_result["success"] is True
    assert target_file.read_bytes() == b"before anchor after"


def test_text_edit_tools_reject_paths_outside_project(tmp_path, monkeypatch):
    project_root = tmp_path / "project"
    project_root.mkdir()
    outside_file = tmp_path / "outside.txt"
    outside_file.write_bytes(b"private text")
    monkeypatch.setattr(server, "PROJECT_DIR", str(project_root))

    result = server.replace_text("../outside.txt", "private", "changed")

    assert result["success"] is False
    assert "relative path inside PROJECT_DIR" in result["error"]
    assert outside_file.read_bytes() == b"private text"
