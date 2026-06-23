# 🌐 System Context Document: Project Reader MCP

```
Status: Draft
Version: 0.1
Last Updated: 2026-06-23
Author(s): Dielson
Related Artifacts: None
```

## 🌟 1. Overview & Goal

This document defines the scope and high-level architecture for **Project Reader MCP**. The primary goal of this system is to expose a set of tools via an MCP interface, allowing a local agents or services to interact with the project file structure and content by using the least amount of resources.

This problem exists because local models usually don't run in an environment with a lot of memory. The standard agentic tools out there are designed to be used with cloud-based models and offer a lot of functionality that unavoidably consumes of lot of the model's context window.

This project is designed to be a lightweight, local solution that allows agents to read, search, and navigate project files through standardized tools.

## 1. Main Features

The system initially aims to provide the following features:

- File listing with metadata (size, last modified timestamp).
- File content reading.
- Recursive search within files for specific patterns (using regex).

## 2. How It Works

The system is built as a Model Context Protocol (MCP) server that exposes a set of tools to an AI agent. The FastMCP framework is used to define the tools and their signatures.

## 3. Key Design Decisions (Linking to ADRs)

- The **FastMCP** framework was chosen for its ease of use and explicit tooling definition.
- For a prototype, the error handling strategy is to simply return an **Error String** instead of raising exceptions directly from the tool signature. This is a temporary measure to simplify the initial implementation and will be revisited in future iterations.
