import os
from dotenv import load_dotenv
import re
from fastmcp import FastMCP


load_dotenv()
PROJECT_DIR = os.environ.get("PROJECT_DIR")

mcp = FastMCP("Project Reader")


@mcp.tool
def list_files() -> list[str]:
    """
    List all files in the project directory.

    Args:
        None (stateless tool).

    Returns:
        A list of strings. Each string is a filename relative to the project root.

        If the directory doesn't exist or an error occurs, the list contains 
        a single descriptive error message string. If the directory is empty, 
        returns ["No files found in directory"].
    """
    target_dir = PROJECT_DIR
    try:
        if not os.path.exists(target_dir):
            return [f"Error: Directory {target_dir} doesn't exist."]
        files = [f for f in os.listdir(target_dir) if os.path.isfile(os.path.join(target_dir, f))]
        return files if files else ["No files found in directory"]

    except Exception as e:
        return [f"Error listing files: {e}"]


@mcp.tool
def read_file(filename: str) -> str:
    """
    Read and return the entire contents of a specific file in the project directory.

    Args:
        filename (str): The name of the file to read relative to the project root.

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

    for filename in target_files:
        matches = _search_single_file(filename, pattern)
        all_matches.extend(matches)

    return all_matches


if __name__ == "__main__":
    mcp.run()
