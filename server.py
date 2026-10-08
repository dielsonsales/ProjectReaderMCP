import os
from pathlib import Path
from dotenv import load_dotenv
import re
from fastmcp import FastMCP
import time
from utils.text_edit_utils import insert_text as insert_text_in_file
from utils.text_edit_utils import replace_text as replace_text_in_file


load_dotenv()
PROJECT_DIR = os.environ.get("PROJECT_DIR")

mcp = FastMCP("Project Reader")


def _get_project_root() -> Path:
    if not PROJECT_DIR:
        raise ValueError("PROJECT_DIR is not configured.")
    try:
        project_root = Path(PROJECT_DIR).resolve(strict=True)
    except (OSError, RuntimeError) as error:
        raise ValueError(f"Project directory '{PROJECT_DIR}' cannot be resolved: {error}") from error
    if not project_root.is_dir():
        raise ValueError(f"Project directory '{PROJECT_DIR}' does not exist or is not a directory.")
    return project_root


def _resolve_project_path(project_root: Path, filename: str) -> Path:
    relative_path = Path(filename)
    if (
        not filename
        or relative_path.is_absolute()
        or ".." in relative_path.parts
        or "\\" in filename
    ):
        raise ValueError("Filename must be a relative path inside PROJECT_DIR.")

    resolved_path = (project_root / relative_path).resolve(strict=True)
    try:
        resolved_path.relative_to(project_root)
    except ValueError as error:
        raise ValueError("Filename resolves outside PROJECT_DIR.") from error
    return resolved_path


def _run_text_edit(filename: str, dry_run: bool, operation, *arguments) -> dict:
    try:
        project_root = _get_project_root()
        file_path = _resolve_project_path(project_root, filename)
        if not file_path.is_file():
            raise ValueError(f"File '{filename}' is not a regular file.")
    except FileNotFoundError:
        return {
            "success": False,
            "dry_run": dry_run,
            "error": f"File '{filename}' was not found in PROJECT_DIR.",
        }
    except (OSError, RuntimeError, ValueError) as error:
        return {"success": False, "dry_run": dry_run, "error": str(error)}

    return operation(file_path, *arguments, dry_run=dry_run)


def format_timestamp(timestamp: float) -> str:
    """
    Converts a UNIX timestamp to a human-readable string format in UTC.
    """
    return time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime(timestamp))


@mcp.tool
def list_files() -> list[tuple[str, dict] | str]:
    """
    Recursively lists all files in the project directory, excluding some specified directories.

    Args:
        None (stateless tool).

    Returns:
        A list of tuples with filename and a dictionary of metadata.

        The filename is a string relative to the project root. The metadata is a dictionary containing file size in
        bytes and last modified timestamp.

        If the directory doesn't exist or an error occurs, the list contains 
        a single descriptive error message string. If the directory is empty, 
        returns ["No files found in directory"].
    """
    try:
        project_root = _get_project_root()
    except ValueError as error:
        return [f"Error: {error}"]

    files = []
    excluded_dirs = {".git", "__pycache__", ".pytest_cache", "venv", ".vscode", "node_modules"}

    try:
        for path in project_root.rglob("*"):
            if not path.is_file():
                continue
            try:
                resolved_path = path.resolve(strict=True)
                relative_path = resolved_path.relative_to(project_root)
            except (OSError, RuntimeError, ValueError):
                continue
            if not any(excluded in relative_path.parts for excluded in excluded_dirs):
                path = resolved_path
                file_size = path.stat().st_size
                last_modified = format_timestamp(path.stat().st_mtime)
                files.append((str(relative_path), {"size": file_size, "last_modified": last_modified}))

    except Exception as e:
        return [f"Error listing files: {e}"]

    return files if files else ["No files found in directory"]


@mcp.tool
def read_file(filename: str) -> str:
    """
    Read and return the entire contents of a specific file in the project directory.

    Args:
        filename (str): The name of the file to read relative to the project root.
                        Can include subdirectories (e.g., "src/utils/helper.py").

    Returns:
        str: The full text content of the file encoded as UTF-8.

        If the file is not found, returns an error message string starting with "Error:".
        If a decoding exception occurs, returns an error message string starting with "Error:".
    """
    try:
        project_root = _get_project_root()
        file_path = _resolve_project_path(project_root, filename)
        if not file_path.is_file():
            return f"Error: File '{filename}' is not a regular file."
        with open(file_path, "r", encoding="utf-8") as f:
            return f.read()

    except ValueError as e:
        return f"Error: {e}"
    except FileNotFoundError:
        return f"Error: File '{filename}' not found in {PROJECT_DIR}."
    except Exception as e:
        return f"Error reading file '{filename}': {e}"


@mcp.tool
def replace_text(filename: str, old_text: str, new_text: str, dry_run: bool = False) -> dict:
    """Replace one unique, exact, case-sensitive text match in a project file.

    Args:
        filename: Existing UTF-8 file path relative to PROJECT_DIR.
        old_text: Non-empty exact text that must occur exactly once. Include a
            line's newline terminator when removing the whole line without
            joining adjacent lines.
        new_text: Replacement text. An empty value removes the matched text.
        dry_run: If true, return the proposed unified diff without writing.

    Returns:
        A result with success, dry_run, and diff on success, or success,
        dry_run, and an actionable error on failure. Zero or multiple matches
        fail without modifying the file.
    """
    return _run_text_edit(
        filename, dry_run, replace_text_in_file, old_text, new_text
    )


@mcp.tool
def insert_text(
    filename: str,
    anchor_text: str,
    text: str,
    position: str = "after",
    dry_run: bool = False,
) -> dict:
    """Insert text before or after one unique, exact, case-sensitive anchor.

    Args:
        filename: Existing UTF-8 file path relative to PROJECT_DIR.
        anchor_text: Non-empty exact text that must occur exactly once.
        text: Text to insert. The anchor remains unchanged.
        position: Insert "before" or "after" the anchor; defaults to "after".
        dry_run: If true, return the proposed unified diff without writing.

    Returns:
        A result with success, dry_run, and diff on success, or success,
        dry_run, and an actionable error on failure. Zero or multiple matches
        fail without modifying the file.
    """
    return _run_text_edit(
        filename, dry_run, insert_text_in_file, anchor_text, text, position
    )


def _search_single_file(project_root: Path, filename: str, pattern: str) -> list[tuple[str, int, str]]:
    """
    Helper to search one file and return results tagged  with the filename

    Args:
        filename (str): Path relative to PROJECT_DIR.
        pattern (str): The regex string to compile and search against.

    Returns:
        list[tuple[str, int, str]]: List of tuples containing (filename, line_number, matched_line_content).

        Returns an empty list if the file cannot be processed.
    """
    matches = []
    try:
        file_path = _resolve_project_path(project_root, filename)
        regex = re.compile(pattern)
        with open(file_path, "r", encoding="utf-8") as f:
            for line_num, line in enumerate(f, 1):
                if regex.search(line):
                    matches.append((filename, line_num, line.rstrip('\n')))
        return matches

    except Exception as e:
        print(f"Warning: Could not process {filename} due to error: {e}")
        return []


@mcp.tool
def recursive_search(pattern: str) -> list[tuple[str, int, str]]:
    """
    Recursively searches for a regex pattern across all files in the project directory.

    Args:
        pattern: The regular expression string to search for.

    Returns:
        A list of tuples: (filename, line_number, line_content) for every match found.
    """
    all_matches = []
    try:
        project_root = _get_project_root()
    except ValueError as error:
        return [(0, 0, f"Error: {error}")]

    file_list_result = list_files()
    if file_list_result and isinstance(file_list_result[0], str) and file_list_result[0].startswith("Error:"):
        return [(0, 0, file_list_result[0])]
    target_files = [item for item in file_list_result if isinstance(item, tuple)]

    if not target_files:
        return [(0, 0, "No files found to search")]

    for item in target_files:
        filename = item[0]
        matches = _search_single_file(project_root, filename, pattern)
        all_matches.extend(matches)

    return all_matches


if __name__ == "__main__":
    mcp.run()
