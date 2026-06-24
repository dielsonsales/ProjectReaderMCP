# Feature: Intelligent File Exclusion via `.gitignore` Parsing

## 1. Problem Statement

The current implementation of `list_files` and `recursive_search` hardcodes excluded directories (e.g., `.git`, `node_modules`) to avoid adding unnecessary files to the search results. This is inflexible because:

1. Different projects/languages have different noise (e.g., `venv` for Python vs `node_modules` for JS).
2. Hardcoding requires code changes for every new environment.
3. It doesn't respect the project's existing "source of truth" for ignored files.

## 2. Proposed Solution

Implement a _Dynamic Exclusion Engine_ that prioritizes project configuration over hardcoded defaults.

The system will automatically detect and parse `.gitignore` files to determine which files/directories to skip during recursive search operations.

### Why `.gitignore`?

- It is a already widely adopted standard for specifying ignored files in version-controlled projects.
- It allows developers to define project-specific exclusions without modifying the codebase.
- Allows the tool to scale across different projects and languages without additional configuration.

## 3. Requirements

- **Compatibility:** Must support standard `.gitignore` syntax (wildcards, negations, recursive patterns).
- **Fallback:** If no `.gitignore` exists, the system must fall back to a default set of common "noise" directories.
- **Performance:** Pattern matching must be efficient to avoid significant overhead during rglob operations on large projects.

## 4. Impact Analysis

- **Complexity:** Low. The parsing logic can be encapsulated in a utility function, and the rest of the code can remain largely unchanged.
- **Performance:** Minimal impact if implemented efficiently. The parsing can be done once and cached if needed.
- **Maintainability:** High. Future changes to ignored files can be managed by simply updating the `.gitignore` file, without touching the codebase.
- **Security:** No new security risks introduced. The feature simply restricts access to certain files and directories.