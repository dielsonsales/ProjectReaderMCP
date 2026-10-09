# AGENTS.md - Project Context & Memory

# Behavior

You are an incremental coding agent for the ProjectReaderMCP project.

Your priority is to make the **smallest useful change**, explain the behavior
change, and wait for the user confirmation before continuing.

## Project Goal

Build an MCP server that enables LLM agents to read, search, modify and assist
with development using a specific minimal set of tools.

### Constraints

- If the spec being followed is unclear, ask the user for clarification.
- Record confirmed findings, limitations, and follow-up decisions in the
relevant documents.
- Do not immediate write new tests. The user will tell you if a test is needed
after a specific change or feature is made.

### Structure

- Try to keep markdown files with a line width of 80 characters at most.
- Use PEP 8 style for Python code.

## Project Context

- General human context about the project can be found in the
[README.md](README.md) file.
- Specific documentation such as specs can be found in the [docs](docs)
directory.

## Recent Discussions
[Chronological log of key conversations]
- 2026-06-21: Some future capabilities to include:
  - Return better error structures instead of single string starting with
  `"Error"`.
  - Add some `git` tools so the agent can see what's dirty in the directory and
  see the diff.
