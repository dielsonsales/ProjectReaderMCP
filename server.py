import os
from pathlib import Path
from dotenv import load_dotenv
import re
from fastmcp import FastMCP
import time


load_dotenv()
PROJECT_DIR = os.environ.get("PROJECT_DIR")

mcp = FastMCP("Project Reader")


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
    project_root = Path(PROJECT_DIR)
    if not project_root.exists() or not project_root.is_dir():
        return [f"Error: Project directory '{PROJECT_DIR}' does not exist or is not a directory."]

    files = []
    excluded_dirs = {".git", "__pycache__", ".pytest_cache", "venv", ".vscode", "node_modules"}

    try:
        for path in project_root.rglob("*"):
            if path.is_file() and not any(excluded in path.parts for excluded in excluded_dirs):
                relative_path = path.relative_to(project_root)
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
    file_path = os.path.join(PROJECT_DIR, filename)
    try:
        if not os.path.exists(file_path):
            return f"Error: File '{filename}' not found in {PROJECT_DIR}."
        with open(file_path, "r", encoding="utf-8") as f:
            return f.read()

    except Exception as e:
        return f"Error reading file '{filename}': {e}"


def _search_single_file(filename: str, pattern: str) -> list[tuple[str, int, str]]:
    """
    Helper to search one file and return results tagged  with the filename

    Args:
        filename (str): Path relative to PROJECT_DIR.
        pattern (str): The regex string to compile and search against.

    Returns:
        list[tuple[str, int, str]]: List of tuples containing (filename, line_number, matched_line_content).

        Returns an empty list if the file cannot be processed.
    """
    file_path = os.path.join(PROJECT_DIR, filename)
    matches = []
    try:
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
    file_list_result = list_files()
    target_files = [f for f in file_list_result if not isinstance(f, str) or not f.startswith("Error")]

    if not target_files:
        return [(0, 0, "No files found to search")]

    for item in target_files:
        if isinstance(item, tuple):
            filename = item[0]
        else:
            filename = item
        matches = _search_single_file(filename, pattern)
        all_matches.extend(matches)

    return all_matches


if __name__ == "__main__":
    mcp.run()
