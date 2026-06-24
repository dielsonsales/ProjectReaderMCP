from pathlib import Path
import os
import pathspec

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
    