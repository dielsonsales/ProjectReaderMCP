import difflib
import os
import stat
import tempfile
from pathlib import Path


def _failure(dry_run: bool, error: str, match_count: int | None = None) -> dict:
    result = {"success": False, "dry_run": dry_run, "error": error}
    if match_count is not None:
        result["match_count"] = match_count
    return result


def _normalize_argument(text: str, name: str) -> str:
    normalized = text.replace("\r\n", "\n")
    if "\r" in normalized:
        raise ValueError(f"{name} contains an unsupported carriage return.")
    return normalized


def _read_text(file_path: Path) -> tuple[str, str, bool, os.stat_result]:
    file_stat = file_path.stat()
    content = file_path.read_bytes().decode("utf-8")

    if "\r" in content:
        normalized = content.replace("\r\n", "")
        if "\r" in normalized or "\n" in normalized:
            raise ValueError("File contains mixed or unsupported newline conventions.")
        newline = "\r\n"
    else:
        newline = "\n"

    logical_content = content.replace("\r\n", "\n")
    return logical_content, newline, logical_content.endswith("\n"), file_stat


def _find_matches(content: str, search_text: str) -> list[int]:
    positions = []
    start = 0
    while True:
        position = content.find(search_text, start)
        if position == -1:
            return positions
        positions.append(position)
        start = position + 1


def _preserve_final_newline(content: str, had_final_newline: bool) -> str:
    if had_final_newline:
        return content if content.endswith("\n") else f"{content}\n"
    return content.rstrip("\n")


def _make_diff(file_path: Path, old_content: str, new_content: str) -> str:
    return "".join(
        difflib.unified_diff(
            old_content.splitlines(keepends=True),
            new_content.splitlines(keepends=True),
            fromfile=f"a/{file_path.name}",
            tofile=f"b/{file_path.name}",
        )
    )


def _atomic_write(file_path: Path, content: bytes, mode: int) -> None:
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{file_path.name}.", suffix=".tmp", dir=file_path.parent
    )
    temporary_path = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "wb") as temporary_file:
            temporary_file.write(content)
            temporary_file.flush()
            os.fsync(temporary_file.fileno())
        os.chmod(temporary_path, mode)
        os.replace(temporary_path, file_path)
    finally:
        try:
            temporary_path.unlink()
        except FileNotFoundError:
            pass


def _edit_text(
    file_path: Path,
    search_text: str,
    text: str,
    position: str | None,
    dry_run: bool,
) -> dict:
    try:
        search_text = _normalize_argument(search_text, "Search text")
        text = _normalize_argument(text, "Inserted or replacement text")
        original, newline, had_final_newline, file_stat = _read_text(file_path)
    except (OSError, UnicodeError, ValueError) as error:
        return _failure(dry_run, str(error))

    matches = _find_matches(original, search_text)
    if len(matches) != 1:
        if not matches:
            return _failure(dry_run, "Exact text was not found.", 0)
        return _failure(
            dry_run,
            f"Exact text must match once; found {len(matches)} matches.",
            len(matches),
        )

    match = matches[0]
    if position == "before":
        updated = original[:match] + text + original[match:]
    elif position == "after":
        updated = original[: match + len(search_text)] + text + original[match + len(search_text) :]
    else:
        updated = original[:match] + text + original[match + len(search_text) :]

    updated = _preserve_final_newline(updated, had_final_newline)
    diff = _make_diff(file_path, original, updated)

    if not dry_run and updated != original:
        encoded_content = updated.replace("\n", newline).encode("utf-8")
        try:
            _atomic_write(file_path, encoded_content, stat.S_IMODE(file_stat.st_mode))
        except OSError as error:
            return _failure(dry_run, f"Could not write file atomically: {error}")

    return {"success": True, "dry_run": dry_run, "diff": diff}


def replace_text(
    file_path: Path, old_text: str, new_text: str, dry_run: bool = False
) -> dict:
    """Replace one unique exact text match in a UTF-8 file."""
    if not old_text:
        return _failure(dry_run, "old_text must not be empty.")
    return _edit_text(file_path, old_text, new_text, None, dry_run)


def insert_text(
    file_path: Path,
    anchor_text: str,
    text: str,
    position: str = "after",
    dry_run: bool = False,
) -> dict:
    """Insert text before or after one unique exact anchor in a UTF-8 file."""
    if not anchor_text:
        return _failure(dry_run, "anchor_text must not be empty.")
    if position not in {"before", "after"}:
        return _failure(dry_run, "position must be 'before' or 'after'.")
    return _edit_text(file_path, anchor_text, text, position, dry_run)