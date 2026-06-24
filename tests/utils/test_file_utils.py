import pytest
from pathlib import Path
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
