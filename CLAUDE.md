# Workspace Instructions

This workspace provides tools and an agent environment for project development.

## Core Principles
- **Dependency Management**: Use [`uv`](https://github.com/astral-sh/uv) for all package management and environment handling.
- **Documentation**: Describe briefly and concise every function - its inputs and outputs data types.
- **Pydantic**: Use Pydantic models for structured data handling where appropriate. Write them inside the `models/` directory.
- **Consts**: Define all constants in a dedicated module for easy management and consistency.
- **Editing**: Avoid to write lines longer than 80 characters to maintain readability.
- **Modularity**: if part of a project is a closed part, do not hesitate to create additional models and consts directories and files, respectively

## Project Structure
- read README.md for project description 