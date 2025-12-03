# Copilot Instructions for Snaprop_Instant

This repository contains the "房估宝" (Property Valuation Treasure) application, a Python Flask-based system for real estate valuation using Intelligent Market Comparison Approach (IMCA) and LLM enhancement.

## Project Architecture

- **Web Framework**: Flask (`app.py` is the main entry point).
- **Database**: MySQL, managed via `database/mysql_manager.py`.
- **LLM Integration**: Alibaba Cloud Dashscope (Qianwen), managed via `llm/llm_manager.py`.
- **Core Logic**:
  - `price/`: Valuation algorithms (`IMCA`, `RealEstateValuation`).
  - `rules/`: Differentiable rule learning framework.
  - `report/`: OCR and report generation.
  - `llm/`: LLM prompts and management.

## Key Components & Patterns

### 1. LLM Integration

- Use `llm.llm_manager.QianwenManager` for all LLM interactions.
- Prompts are centralized in `llm/prompt.py`.
- **Pattern**:
  ```python
  from llm.llm_manager import QianwenManager
  qm = QianwenManager()
  response = qm.interact_qwen(prompt="...", request="...")
  ```

### 2. Database Access

- Use `database.mysql_manager.MySQLManager` for database operations.
- **Pattern**:
  ```python
  from database.mysql_manager import MySQLManager
  db = MySQLManager()
  cursor = db.get_cursor()
  # ... execute queries ...
  db.close()
  ```
- Configuration is in `config/mysql_config.py`.

### 3. Valuation Logic (IMCA)

- The core valuation logic resides in `price/imca.py` within the `IMCA` class.
- It uses a `DifferentiableRuleLearningFramework` from `rules/differentiable_rule.py`.
- When modifying valuation logic, ensure `IMCA` and `RealEstateValuation` are consistent.

### 4. Configuration

- All configuration files are in `config/`.
- Do not hardcode API keys or database credentials; use the config files.
- `path_config.py` manages file paths.

### 5. Data Handling

- `pandas` is the primary library for data manipulation.
- `openpyxl` is used for Excel interactions.

## Development Workflow

- **Dependencies**: Managed in `requirements.txt`.
- **Running the App**:
  ```bash
  python app.py
  ```
- **Static Files**: Uploads go to `static/uploads`, reports to `static/reports`.

## Coding Standards

- **Imports**: Use absolute imports from the project root (e.g., `from llm.prompt import Prompt`).
- **Error Handling**: Use `try-except` blocks for imports to handle optional dependencies gracefully, as seen in `main.py`.
- **Comments**: Docstrings are encouraged for classes and functions.
