# Workspace Instructions

This workspace provides tools and an agent environment for project development.

## Core Principles
- **Dependency Management**: Use [`uv`](https://github.com/astral-sh/uv) for all package management and environment handling.
- **Documentation**: Describe briefly and concise every function - its inputs and outputs data types.
- **Pydantic**: Use Pydantic models for structured data handling where appropriate. Write them inside the `models/` directory.
- **Consts**: Define all constants inside the `consts/` directory, one module per project part (e.g. `consts/cards.py`, `consts/web.py`), for easy management and consistency.
- **Editing**: Avoid to write lines longer than 80 characters to maintain readability.
- **Modularity**: keep models and consts centralized in `models/` and `consts/` (no `consts.py` / `models/` inside other packages). For a new, closed part of the project, add the necessary subdirectory or module in `models/` and `consts/` if reasonable.

## Project Structure
- read README.md for project description 