from pathlib import Path
import os
import pathspec


def read_lines(file_path: Path, start_line: int, end_line: int) -> tuple[bool, str | None]:
    """
    Read a contiguous range of lines from a file.

    Args:
        file_path: Path to the file (must exist and be a regular file).
        start_line: 1-based inclusive starting line number.
        end_line: 1-based inclusive ending line number (may extend beyond EOF).

    Returns:
        A tuple of (success, content_or_error):
        - On success: (True, str) where str is the selected lines with original line terminators.
        - On failure: (False, error_message) where error_message starts with "Error:".

    Constraints:
        - start_line must be >= 1 and <= end_line.
        - If start_line is beyond EOF, returns empty string (not an error).
        - If end_line is beyond EOF, reads through actual file end.
        - Only selected lines are decoded as UTF-8; skipped lines may have invalid UTF-8.
        - Line terminators (LF or CRLF) are preserved exactly as in source.
    """
    # Validate line number types (reject booleans, floats, None)
    if isinstance(start_line, bool) or isinstance(end_line, bool):
        return (False, "Error: Line numbers must be integers, not booleans.")

    if not isinstance(start_line, int) or not isinstance(end_line, int):
        return (False, "Error: Line numbers must be integers.")

    # Validate line number ranges
    if start_line < 1:
        return (False, "Error: start_line must be >= 1.")

    if end_line < 1:
        return (False, "Error: end_line must be >= 1.")

    if start_line > end_line:
        return (False, "Error: start_line must not exceed end_line.")

    # Check file exists
    if not file_path.exists():
        return (False, f"Error: File '{file_path}' does not exist.")

    if not file_path.is_file():
        return (False, f"Error: '{file_path}' is not a regular file.")

    try:
        with open(file_path, "rb") as f:
            selected_lines = []
            line_number = 0

            while line_number < end_line:
                line = f.readline()
                if not line:
                    break

                line_number += 1
                if line_number < start_line:
                    continue

                try:
                    selected_lines.append(line.decode("utf-8"))
                except UnicodeDecodeError:
                    return (
                        False,
                        f"Error: File contains invalid UTF-8 in line {line_number}.",
                    )

            return (True, "".join(selected_lines))

    except PermissionError:
        return (False, f"Error: Permission denied reading file '{file_path}'.")
    except Exception as e:
        return (False, f"Error reading file '{file_path}': {e}")


def get_gitignore_matcher(project_dir: str) -> pathspec.PathSpec:
    """
    Returns a Pathspec matcher for the .gitignore file in the given project directory.
    If no .gitignore file is found, returns an empty matcher.
    """
    gitignore_path = Path(project_dir) / ".gitignore"

    if not gitignore_path.exists():
        # Returns an empty matcher
        return pathspec.PathSpec.from_lines(pathspec.patterns.gitignore.spec.GitIgnoreSpecPattern, [])

    try:
        with open(gitignore_path, "r") as f:
            content = f.read().splitlines()
            return pathspec.PathSpec.from_lines(pathspec.patterns.gitignore.spec.GitIgnoreSpecPattern, content)
    except Exception as e:
        print(f"Warning: Could not read .gitignore due to error: {e}")
        return pathspec.PathSpec.from_lines(pathspec.patterns.gitignore.spec.GitIgnoreSpecPattern, [])


def is_ignored(file_path: Path, project_root: Path, matcher: pathspec.PathSpec) -> bool:
    """
    Checks if a given path is ignored based on its relative path to the project root.
    """
    try:
        relative_path_str = file_path.relative_to(project_root).as_posix()
        return matcher.match_file(relative_path_str)
    except ValueError:
        # If file_path is not a subpath of project_root
        return False
    