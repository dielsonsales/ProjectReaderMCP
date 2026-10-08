# Exact Text Editing Capability

- **type:** Feature
- **status:** Implemented
- **author:** Dielson Sales de Carvalho
- **created_at:** 2026-10-08T00:00:00Z
- **last_updated:** 2026-10-08T00:00:00Z

## Outcome
The MCP server will provide exact-text tools for replacing and inserting text in
one existing file. Agents can request a focused edit without constructing a
unified diff or rewriting an entire file.

## Problem
Unified diffs require valid syntax, including exact hunk counts, path headers,
line prefixes, and real line breaks. LLM-generated diffs can fail on these
formatting requirements before the intended edit is considered. For a small,
localized change, an API based on exact text already read from the file can be
easier to construct and validate.

## Hypothesis
Providing `replace_text` and `insert_text` tools that require a unique exact
match will make common edits simpler while retaining safeguards against stale,
ambiguous, or unintended modifications. Requiring a dry-run option, preserving
newline conventions, and writing atomically will keep the operation reviewable
and protect the original file from partial updates.

## Scope
- Add a `replace_text` tool for replacing or removing one exact text range.
- Add an `insert_text` tool for inserting text immediately before or after one
  exact anchor.
- Require the target to be one existing UTF-8 file inside `PROJECT_DIR`.
- Require exact, case-sensitive matching and exactly one match for every
  non-empty search string or anchor.
- Support a `dry_run` option that returns the proposed unified diff without
  modifying the file.
- Preserve the file's newline convention and apply successful changes
  atomically.

## Out of Scope
- Regex, fuzzy, case-insensitive, or whitespace-normalized matching.
- Replacing all occurrences or selecting one match by occurrence number.
- Creating or deleting files, binary-file editing, and edits outside
  `PROJECT_DIR`.
- Syntax-aware or AST-based edits.

## Constraints
- **Safety**: Resolve the requested filename using the existing project path
  validation. Never write outside `PROJECT_DIR`.
- **Exactness**: Match the supplied text literally and case-sensitively. Do not
  trim, normalize whitespace, or select a match based on line numbers.
- **Uniqueness**: A replacement range or insertion anchor must match exactly
  once. If it matches zero or multiple times, return an error and leave the
  file unchanged.
- **Deletion**: `replace_text` accepts an empty `new_text`. To remove a whole
  line without joining adjacent lines, `old_text` must include that line's
  newline terminator when present.
- **Insertion**: `insert_text` requires a non-empty anchor and a `position` of
  `before` or `after`. The anchor remains in the file; only the supplied text
  is inserted. Inserting into an empty file is not supported by this anchored
  operation.
- **Line Endings**: Treat LF in tool arguments as the logical newline for
  matching. Normalize the file's LF or CRLF line endings for matching, convert
  inserted or replacement text to the file's original convention, and preserve
  the original final-newline state. Reject mixed or unsupported newline
  conventions rather than normalizing the whole file.
- **Atomicity**: Read and validate the complete edit before writing. A failed
  validation or I/O operation must not leave a partial edit.
- **Encoding**: Support UTF-8 text only. Reject invalid UTF-8 without
  modification.
- **Dry Run**: A dry run must return the resulting diff and must not change file
  contents or metadata.

## Proposed Change

### 1. Text Editing Utilities
Implement the core logic in a focused utility module, such as
`utils/text_edit_utils.py`, or in an existing file utility module if that better
fits the implementation.

- `replace_text(file_path: Path, old_text: str, new_text: str,
  dry_run: bool = False)` finds one exact occurrence of `old_text` and replaces
  it with `new_text`. An empty `new_text` removes the matched text. An empty
  `old_text` is invalid.
- `insert_text(file_path: Path, anchor_text: str, text: str,
  position: str = "after", dry_run: bool = False)` finds one exact occurrence
  of `anchor_text` and inserts `text` immediately before or after it. Empty
  anchors and positions other than `before` or `after` are invalid.
- Both operations return a result containing `success`, `dry_run`, and a diff
  on success. Failures return `success: false` and an actionable `error`; a
  match count may be included to help the caller choose a more specific anchor.
- Reuse shared encoding, newline-preservation, diff-generation, and atomic-write
  helpers where practical. Do not duplicate path resolution in the utility.

### 2. Update `server.py`
- Register MCP tools for `replace_text` and `insert_text`.
- Resolve and validate `filename` with the existing project-root helpers before
  calling the utility functions.
- Provide tool descriptions that state matching is exact and case-sensitive,
  anchors or old text must be unique, `new_text` may be empty for removal, and
  `dry_run` does not write changes.
- Return a consistent structured result for success and failure.

### 3. Data Flow
1. The agent reads a file and calls `replace_text` with the relative filename,
   exact old text, replacement text, and optionally `dry_run=True`.
2. `server.py` resolves the existing file and verifies it is inside
   `PROJECT_DIR`.
3. The text-edit utility validates encoding and newline style, counts exact
   matches, and rejects zero or multiple matches without writing.
4. The utility computes the updated content and unified diff in memory. For a
   dry run it returns the diff; otherwise it atomically writes the updated
   content while preserving the file's newline convention and permissions.
5. For insertion, the same flow applies, with the utility inserting text
   before or after the uniquely matched anchor without removing the anchor.

### 4. Error and Cancellation Behavior
- **File Not Found / Invalid Path**: Return an actionable error and do not
  modify any file.
- **Invalid Input**: Reject an empty search string or anchor, invalid insertion
  position, or invalid UTF-8 input.
- **No Match**: Report that the exact text was not found; leave the file
  unchanged.
- **Multiple Matches**: Report the number of matches and require a more
  specific old-text range or anchor; do not guess.
- **Unsupported Newlines**: Reject mixed or unsupported newline conventions
  without modifying the file.
- **Permission Denied / I/O Failure**: Return an error. The original file must
  remain intact if atomic replacement has not completed.
- **Dry Run**: Return the proposed diff without changing file contents or
  metadata.

## Acceptance Criteria

- [ ] Given old text that occurs exactly once, when `replace_text` is called,
    then only that range is replaced and unrelated content is preserved.
- [ ] Given a non-empty old text and an empty replacement, when `replace_text`
    is called, then the matched text is removed; including a line terminator
    removes a complete line without joining adjacent lines.
- [ ] Given an anchor that occurs exactly once, when `insert_text` is called
    with `before` or `after`, then the text is inserted at that location and
    the anchor remains unchanged.
- [ ] Given old text or an anchor that occurs zero or multiple times, when
    either tool is called, then it returns an actionable error and does not
    modify the file.
- [ ] Given a dry-run request, when either tool is called, then it returns the
    proposed diff and leaves file contents and metadata unchanged.
- [ ] Given an LF or CRLF file, when a valid edit is applied, then the file's
    original newline convention and final-newline state are preserved.
- [ ] Given an invalid path, invalid UTF-8 file, unsupported newline style, or
    write failure, when either tool is called, then the file is not partially
    modified.

## Validation Plan
- **Unit Tests**: Test unique replacement, deletion, insertion before and after
  an anchor, missing and ambiguous matches, invalid arguments, empty-file
  behavior, dry runs, UTF-8 failures, LF/CRLF preservation, final-newline
  preservation, and atomic failure.
- **Integration Test**: Invoke both tools through the MCP test client using a
  temporary project root; verify returned diffs, path restrictions, dry-run
  behavior, and on-disk contents.
- **Manual Check**: Use an MCP client to replace a unique code or documentation
  block, remove a complete line, and insert text before/after an anchor. Confirm
  that an ambiguous anchor fails without modifying the file.

## Risks and Open Questions
- **Anchor Quality**: Short or common text is likely to be ambiguous. Tool
  descriptions should tell agents to include enough surrounding text to select
  one occurrence.
- **Retries**: Insertion is not inherently idempotent; a client that loses a
  successful response should read the file again before retrying.
- **Line Endings**: Newline normalization must not alter unrelated content or
  the file's final-newline state.
- **Result Shape**: Decide whether to return a numeric match count on failures
  or keep the result limited to `success` and `error` for compatibility with
  existing MCP tool results.
