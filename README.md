# Project Reader MCP Server

This repository implements a Model Context Protocol (MCP) server designed to expose filesystem operations as callable tools to an AI agent. It provides controlled, sandboxed access to read directory contents and file contents within a specified project root.

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

The server requires a `.env` file in the root directory to specify which target project folder the tools are allowed to access.

Create a `.env` file:
```env
PROJECT_DIR="/absolute/path/to/your/target/project"
```

💡 Tip: Always use absolute paths to prevent relative paths from resolving incorrectly.

### Interactive Testing (FastMCP Inspector)

FastMCP includes a built-in graphical inspector tool. This spins up a web interface where you can manually invoke your server's tools and view their exact JSON outputs with hot-reloading enabled.

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
