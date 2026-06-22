# AGENTS.md - Project Context & Memory

## Project Goal
Build an MCP server that enables LLM agents to read, search, and navigate a project files through standardized tools.

## Key Decisions & Rationale
- [Decision 1](#decision-1) with reasoning
- [Decision 2](#decision-2) with trade-offs considered

## Technical Context
- Architecture patterns used
- Key constraints (performance, security, etc.)
- Unresolved questions/TODOs

## Recent Discussions
[Chronological log of key conversations]
- 2026-06-21: Some future capabilities to include:
  - Expand `list_files` to return more than just names, but also metadata (e.g., file size, last modified date).
  - Add a tool to read specific line ranges (e.g., `read_lines(filename, start_line, end_line)`).
  - Return better error structures instead of single string starting with `"Error"`.
  - Add some `git` tools so the agent can see what's dirty in the directory and see the diff.

## Tasks

[x] Add metadata information in the `list_files` tool function.
[ ] Implement a new tool function `read_lines` that reads specific line ranges from a file.
[ ] Refactor error handling to return structured error information instead of plain strings.
[ ] Implement git-related tools for checking dirty files and viewing diffs.
