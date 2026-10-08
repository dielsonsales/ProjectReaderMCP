# Project Reader MCP Server

This repository implements a Model Context Protocol (MCP) server designed to
expose filesystem operations as callable tools to an AI agent. It provides
controlled, sandboxed access to read directory contents and file contents within
a specified project root.

## Getting Started

### Prerequisites

Create a virtual environment so you can install the dependencies:

```bash
python3 -m venv venv
```

Install the required dependencies listed in `requirements.txt`:

```bash
pip install -r requirements.txt
```

## Development, Testing & Troubleshooting

### Configuration

The server requires a `.env` file in the root directory to specify which target
project folder the tools are allowed to access.

Create a `.env` file:
```env
PROJECT_DIR="/absolute/path/to/your/target/project"
```

💡 Tip: Always use absolute paths to prevent relative paths from resolving
incorrectly.

## Available Tools

The server exposes the following tools to the agent. All paths must be relative
to `PROJECT_DIR` and resolve inside it; the server never reads or writes outside
that directory.

- **`list_files`** – Recursively lists every file in the project (excluding
noise directories such as `.git`, `venv`, `node_modules`) together with its size
and last-modified timestamp.
- **`read_file(filename)`** – Reads and returns the full UTF-8 contents of a
single file.
- **`recursive_search(pattern)`** – Searches all project files for a regex
pattern and returns the matching lines with their file and line numbers.
- **`replace_text(filename, old_text, new_text, dry_run=False)`** – Replaces one
unique, exact, case-sensitive occurrence of `old_text` with `new_text`. An empty
`new_text` removes the matched text.
- **`insert_text(filename, anchor_text, text, position="after", dry_run=False)`** – Inserts
`text` immediately before or after one unique, exact anchor, leaving the anchor in place.

### Editing with `replace_text` and `insert_text`

These tools make small, localized edits simpler for an agent: it supplies the
exact text it already read from the file rather than constructing a unified
diff.

- **Exact and unique matching** – The search text/anchor must match exactly
(case-sensitive) and exactly once. If it matches zero times or multiple times,
the tool returns an actionable error and leaves the file unchanged (failures
include a `match_count` to help you disambiguate).
- **Dry run** – Pass `dry_run=True` to get the proposed unified diff without
modifying the file's contents or metadata.
- **Result shape** – Both tools return a structured object:
`{success, dry_run, diff}` on success, or `{success, dry_run, error}` (and
`match_count` where relevant) on failure.

See [`docs/specs/001-exact-text-editing.md`](docs/specs/001-exact-text-editing.md)
for the full specification.

## Development, Testing & Troubleshooting

### Interactive Testing (FastMCP Inspector)

FastMCP includes a built-in graphical inspector tool. This spins up a web
interface where you can manually invoke your server's tools and view their exact
JSON outputs with hot-reloading enabled.

Run the inspector:

```bash
fastmcp dev inspector server.py
```

## Adding the MCP server to LM Studio

Edit your `mcp.json` file to look like this:

```json
{
  "mcpServers": {
    "project_reader": {
      "command": "/path/to/your/project/directory/project-reader-mcp/venv/bin/python",
      "args": [
        "/path/to/your/project/directory/project-reader-mcp/server.py"
      ]
    }
  }
}
```
