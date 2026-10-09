import pytest
from pathlib import Path
from utils import file_utils
from utils.file_utils import get_gitignore_matcher, is_ignored

@pytest.fixture
def mock_project_dir(tmp_path):
    """
    Creates a dummy project directory with a .gitignore file for testing and some files and directories it should
    ignore.
    """
    gitignore = tmp_path / ".gitignore"
    gitignore.write_text("node_modules/\n*.log\n")

    # Files that should be ignored
    (tmp_path / "node_modules").mkdir()
    (tmp_path / "node_modules" / "test.js").write_text("console.log('hello world');")
    (tmp_path / "debug.log").write_text("Some debug information.")

    # Files that should NOT be ignored
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "main.js").write_text("console.log('hello world');")

    return tmp_path


def test_is_ignored_positive(mock_project_dir):
    matcher = get_gitignore_matcher(str(mock_project_dir))

    assert is_ignored(mock_project_dir / "node_modules" / "test.js", mock_project_dir, matcher)
    assert is_ignored(mock_project_dir / "debug.log", mock_project_dir, matcher)


def test_is_ignored_negative(mock_project_dir):
    matcher = get_gitignore_matcher(str(mock_project_dir))
    assert is_ignored(mock_project_dir / "src" / "main.js", mock_project_dir, matcher) is False


def test_missing_gitignore(tmp_path):
    """
    Tests the behavior when no .gitignore file is present in the project directory.
    """
    # Create a dummy project directory without a .gitignore
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "main.js").write_text("console.log('hello world');")

    matcher = get_gitignore_matcher(str(tmp_path))
    assert is_ignored(tmp_path / "src" / "main.js", tmp_path, matcher) is False


@pytest.mark.parametrize(
    ("start_line", "end_line", "expected"),
    [
        (1, 1, "first\r\n"),
        (2, 2, "second\n"),
        (3, 3, "third"),
        (2, 3, "second\nthird"),
    ],
)
def test_read_lines_returns_inclusive_range_with_original_endings(
    tmp_path, start_line, end_line, expected
):
    target = tmp_path / "target.txt"
    target.write_bytes(b"first\r\nsecond\nthird")

    success, result = file_utils.read_lines(target, start_line, end_line)

    assert success is True
    assert result == expected


@pytest.mark.parametrize(
    ("content", "start_line", "end_line", "expected"),
    [
        (b"", 1, 1, ""),
        (b"first\nlast", 3, 5, ""),
        (b"first\nlast", 2, 9, "last"),
        (b"first\nlast", 1, 9, "first\nlast"),
    ],
)
def test_read_lines_handles_empty_and_out_of_file_ranges(
    tmp_path, content, start_line, end_line, expected
):
    target = tmp_path / "target.txt"
    target.write_bytes(content)

    success, result = file_utils.read_lines(target, start_line, end_line)

    assert success is True
    assert result == expected


@pytest.mark.parametrize(
    ("start_line", "end_line"),
    [
        (0, 1),
        (1, 0),
        (2, 1),
        (True, 1),
        (1, False),
        (1.5, 2),
        ("1", 2),
        (None, 1),
    ],
)
def test_read_lines_rejects_invalid_ranges(tmp_path, start_line, end_line):
    target = tmp_path / "target.txt"
    target.write_bytes(b"content\n")

    success, result = file_utils.read_lines(target, start_line, end_line)

    assert success is False
    assert result.startswith("Error:")


def test_read_lines_reports_missing_file(tmp_path):
    success, result = file_utils.read_lines(tmp_path / "missing.txt", 1, 1)

    assert success is False
    assert result.startswith("Error:")


def test_read_lines_rejects_directory(tmp_path):
    success, result = file_utils.read_lines(tmp_path, 1, 1)

    assert success is False
    assert result.startswith("Error:")
    assert "not a regular file" in result


def test_read_lines_reports_read_failure(tmp_path, monkeypatch):
    target = tmp_path / "target.txt"
    target.write_bytes(b"content\n")

    def fail_open(path, mode):
        raise PermissionError("permission denied")

    monkeypatch.setattr(file_utils, "open", fail_open, raising=False)

    success, result = file_utils.read_lines(target, 1, 1)

    assert success is False
    assert result.startswith("Error:")
    assert "Permission denied" in result


def test_read_lines_ignores_invalid_utf8_in_skipped_lines(tmp_path):
    target = tmp_path / "target.txt"
    target.write_bytes(b"\xff\nskipped\nselected\n")

    success, result = file_utils.read_lines(target, 3, 3)

    assert success is True
    assert result == "selected\n"


def test_read_lines_rejects_invalid_utf8_without_returning_partial_content(tmp_path):
    target = tmp_path / "target.txt"
    target.write_bytes(b"prefix\nselected\xff\n")

    success, result = file_utils.read_lines(target, 1, 2)

    assert success is False
    assert result.startswith("Error:")
    assert "prefix" not in result


def test_read_lines_stops_at_requested_end_line(tmp_path, monkeypatch):
    target = tmp_path / "target.txt"
    target.write_bytes(b"first\nsecond\n\xff\n")
    original_open = open

    class TrackedReader:
        def __init__(self, path, mode):
            self.file = original_open(path, mode)
            self.readline_calls = 0

        def __enter__(self):
            return self

        def __exit__(self, *args):
            self.file.close()

        def readline(self):
            self.readline_calls += 1
            return self.file.readline()

    readers = []

    def tracked_open(path, mode):
        reader = TrackedReader(path, mode)
        readers.append(reader)
        return reader

    monkeypatch.setattr(file_utils, "open", tracked_open, raising=False)

    success, result = file_utils.read_lines(target, 1, 2)

    assert success is True
    assert result == "first\nsecond\n"
    assert readers[0].readline_calls == 2


def test_read_lines_does_not_modify_file_contents_or_metadata(tmp_path):
    target = tmp_path / "target.txt"
    original_content = b"first\r\nsecond"
    target.write_bytes(original_content)
    original_stat = target.stat()

    success, result = file_utils.read_lines(target, 1, 2)

    updated_stat = target.stat()
    assert success is True
    assert result == "first\r\nsecond"
    assert target.read_bytes() == original_content
    assert updated_stat.st_size == original_stat.st_size
    assert updated_stat.st_mtime_ns == original_stat.st_mtime_ns
