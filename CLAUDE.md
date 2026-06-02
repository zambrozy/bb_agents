# Workspace Instructions

This workspace provides tools and an agent environment for project development.

## Core Principles
- **Dependency Management**: Use [`uv`](https://github.com/astral-sh/uv) for all package management and environment handling.
- **Documentation**: Describe briefly and concise every function - its inputs and outputs data types.
- **Pydantic**: Use Pydantic models for structured data handling where appropriate. Write them inside the `models/` directory.
- **Consts**: Define all constants in a dedicated module for easy management and consistency.
- **Editing**: Avoid to write lines longer than 80 characters to maintain readability.

## Project Structure
- `.venv/`: Managed by `uv`, targeting Python 3.14.