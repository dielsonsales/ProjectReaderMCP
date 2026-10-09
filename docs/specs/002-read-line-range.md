# Read Line Range Capability

- **type:** Feature
- **status:** Proposed
- **author:** Dielson Sales de Carvalho
- **created_at:** 2026-10-08T00:00:00Z
- **last_updated:** 2026-10-08T00:00:00Z

## Outcome
The MCP server will provide a `read_lines` tool that returns a requested range
from one project file without returning the entire file. Agents can inspect a
focused portion of a large file and retain its original line boundaries.

## Problem
`read_file` returns the entire contents of a file, which can consume more
context than needed when an agent only needs to inspect a small section. A line
range reader will allow callers to request just the relevant portion while
using the same project-root access restrictions as the existing read tool.

## Hypothesis
A `read_lines(filename, start_line, end_line)` tool with 1-based inclusive line
numbers, validation of caller-supplied numbers, and exact preservation of
selected line terminators will let agents read focused sections predictably.
Ignoring requested lines that fall outside the file will let callers request a
range through EOF without first knowing the file's length.

## Scope
- Add a `read_lines` tool that reads a contiguous range from one existing file.
- Use 1-based line numbers and treat both `start_line` and `end_line` as
  inclusive.
- Return the selected lines as UTF-8 text, retaining each selected line's
  original line terminator when present.
- Require the target to resolve to a regular file inside `PROJECT_DIR`.
- Validate line arguments and report actionable errors for invalid ranges,
  missing files, and decoding or I/O failures.

## Out of Scope
- Changing the behavior or result shape of `read_file`.
- Returning line numbers or metadata alongside the selected text.
- Byte offsets, columns, ranges selected by text, or non-contiguous ranges.
- Refactoring existing tools to return structured errors.
- Editing files or creating files that do not already exist.

## Constraints
- **Path Safety**: Resolve `filename` using the existing project path
  validation. Reject absolute paths, traversal, and paths that resolve outside
  `PROJECT_DIR`.
- **Range Semantics**: `start_line` and `end_line` are positive integers;
  `start_line` must not exceed `end_line`. Lines outside the file's actual
  range are ignored: a start before line 1 is invalid, while an end beyond
  end-of-file is treated as the end of the file. A start beyond end-of-file
  returns an empty string.
- **Line Definition**: Lines are separated by LF or CRLF. A final line without
  a line terminator is still a line. An empty file contains zero lines.
- **Output**: Return only the requested range, in source order, as UTF-8 text.
  Return the intersection of the requested range and the lines in the file.
  Include line terminators where they exist in the selected range; do not add
  a terminator to a selected final line that has none. Return an empty string
  if the intersection is empty, including when the file is empty or
  `start_line` is beyond end-of-file.
- **Encoding**: Support UTF-8 text only. Strictly decode the selected lines;
  invalid UTF-8 in those lines must return an error without returning partial
  content. Do not reject a request because unselected lines contain invalid
  UTF-8.
- **Read-Only**: The operation must not modify file contents or metadata.
- **Compatibility**: Follow the existing read-tool error convention by
  returning a descriptive string prefixed with `Error:` for failures. A future
  structured-error change is separate work.
- **Resource Use**: Read only as much of the file as required to reach
  `end_line` or end-of-file, whichever comes first; do not load the entire file
  when the requested range is near the beginning. The returned value is
  necessarily proportional to the selected range.

## Proposed Change

### 1. Line-Range Reading Utility
Implement the line-range extraction in `utils/file_utils.py` or another
existing file-reading utility module that fits the project structure.

- Accept a validated file path and 1-based inclusive `start_line` and
  `end_line` values.
- Reject booleans and non-integer values as line numbers, as well as values
  below 1 or a start greater than the end.
- Locate line boundaries while streaming and strictly decode only the selected
  lines as UTF-8, preserving their source line terminators. Do not decode or
  validate skipped lines before `start_line`.
- Stop at `end_line` or end-of-file, whichever comes first. If
  `start_line` is beyond end-of-file, return an empty string rather than an
  error.
- Avoid reading lines after `end_line`. If UTF-8 validation of the complete
  file is required by the implementation, document the associated resource
  trade-off; however, full-file UTF-8 validation is not part of this contract.

### 2. Update `server.py`
- Register an MCP tool with the signature
  `read_lines(filename: str, start_line: int, end_line: int) -> str`.
- Resolve and validate `filename` with the existing project-root helpers
  before reading.
- Document that line numbers are 1-based and inclusive, that the end line
  may extend beyond end-of-file, and that selected line terminators are
  retained.
- Return the selected text on success and a descriptive `Error:` string on
  failure, consistent with `read_file`.

### 3. Data Flow
1. The agent calls `read_lines` with a project-relative filename and an
   inclusive line range.
2. `server.py` resolves the project root and verifies the requested path stays
   inside it and names a regular file.
3. The read utility validates the line numbers, reads and decodes the requested
  content through `end_line` or end-of-file, whichever comes first.
4. The tool returns the available selected text, retaining source line endings,
  or returns an actionable error without changing the file.

### 4. Error and Cancellation Behavior
- **File Not Found / Invalid Path**: Return an actionable error and do not
  access files outside `PROJECT_DIR`.
- **Invalid Range**: Reject non-integer or non-positive endpoints and ranges
  where `start_line` is greater than `end_line`.
- **Out of Bounds**: Ignore requested lines beyond end-of-file. If
  `start_line` is beyond end-of-file, return an empty string.
- **Empty File**: Return an empty string for any otherwise valid range because
  there are no lines to return.
- **Invalid UTF-8 / I/O Failure**: Invalid UTF-8 in selected lines returns an
  error rather than partial output. Invalid UTF-8 in unselected lines does not
  affect the result. The file remains unchanged.
- **Read-Only**: All success and failure paths leave file contents and metadata
  unchanged.

## Acceptance Criteria

- [ ] Given a valid range in a UTF-8 file, when `read_lines` is called, then it
  returns exactly the selected lines and no content outside the range.
- [ ] Given line numbers starting at 1 and an inclusive end line, when a single
  line is requested, then exactly that line is returned.
- [ ] Given LF or CRLF content, when a range is read, then selected line
  terminators are preserved, including the absence of a terminator on a final
  line when applicable.
- [ ] Given a range with a start greater than the end, a non-positive endpoint,
  or a non-integer endpoint, when the tool is called, then it returns an
  actionable error.
- [ ] Given an end line beyond end-of-file, when the tool is called, then it
  returns the available lines through EOF without an out-of-range error.
- [ ] Given a start line beyond end-of-file or a request against an empty file,
  when the tool is called with otherwise valid bounds, then it returns an
  empty string.
- [ ] Given invalid UTF-8 in a selected line, an invalid path, or a read
  failure, when the tool is called, then it returns an error and does not
  expose partial content.
- [ ] Given invalid UTF-8 only in lines outside the requested range, when the
  tool is called, then it returns the selected lines without an encoding
  error.
- [ ] Given any request, when the tool completes, then it has not modified file
  contents or metadata.
- [ ] Given a short requested range near the beginning of a large file, when
  the tool reads it, then it does not read lines after the requested end line.

## Validation Plan
- **Unit Tests**: Test first, middle, and final lines; single-line ranges;
  inclusive endpoints; LF and CRLF; final lines with and without terminators;
  empty files; invalid types and bounds; ranges extending beyond EOF; starts
  beyond EOF; invalid UTF-8 in selected lines; invalid UTF-8 in skipped lines;
  read failures; and proof that lines after `end_line` are not read.
- **Integration Test**: Invoke `read_lines` through the MCP test client using a
  temporary project root; verify returned text, path restrictions, errors, and
  unchanged file contents and metadata.
- **Manual Check**: Read a small section from a large source file and confirm
  line numbering, range inclusivity, and retained line endings.
