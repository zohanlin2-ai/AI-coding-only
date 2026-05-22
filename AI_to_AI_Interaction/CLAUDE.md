# CLAUDE.md

## Development and Test Commands
- **Run Unit Tests**: `python -m unittest test_app.py`
- **Run Application**: `streamlit run app.py`
- **Install Dependencies**: `pip install -r requirements.txt`

## Behavioral Guidelines
1. **Think Before Coding**: State assumptions explicitly. Stop and ask if requirements are ambiguous. Present tradeoffs.
2. **Simplicity First**: Write the minimum amount of code to solve the problem. Do not add speculative features or unnecessary complexity.
3. **Surgical Changes**: Only modify code relevant to the task. Match the existing style and clean up only your own changes.

## Code Style & Formatting
- **Python Style**: Follow PEP 8 guidelines.
- **Naming Conventions**: Use snake_case for functions and variables, PascalCase for classes, and UPPERCASE for constants.
- **Imports**: Organize imports (standard library first, third-party libraries second, local modules third).
- **Type Hints**: Use type annotations for function signatures where appropriate to improve readability.
- **Docstrings**: Provide concise docstrings for all modules, classes, and main functions.
