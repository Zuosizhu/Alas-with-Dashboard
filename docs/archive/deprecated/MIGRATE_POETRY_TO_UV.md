### Step-by-Step Migration Plan

If you decide to proceed, here is a detailed plan to migrate from Poetry to UV.

**Phase 1: Preparation and Analysis**

1.  **Create a New Git Branch:** Before making any changes, create a backup of your current state.
    ```bash
    git checkout -b feature/migrate-to-uv
    ```
2.  **Install UV:** Ensure you have UV available on your system.
    ```bash
    pip install uv
    ```
3.  **Analyze Existing Dependencies:** Examine the `pyproject.toml` file to understand the project's dependencies, including development dependencies and any dependency groups. This will help you ensure they are all migrated correctly.

**Phase 2: Core Dependency Migration**

4.  **Generate `requirements.txt` from `pyproject.toml`:** Use UV to compile the dependencies from your `pyproject.toml` into `requirements.txt` files.
    *   For main dependencies:
        ```bash
        uv pip compile pyproject.toml -o requirements.txt
        ```
    *   For development or other dependency groups (assuming a group named 'dev'):
        ```bash
        uv pip compile pyproject.toml --extra dev -o requirements-dev.txt
        ```
5.  **Update `.gitignore`:** Add the new virtual environment directory to your `.gitignore` file to avoid committing it.
    ```
    # Virtual Environment
    .venv/
    ```
6.  **De-Poetry-fy `pyproject.toml`:** This is a critical step. You need to remove Poetry as the project manager.
    *   **Remove** the `[tool.poetry]` section entirely.
    *   **Keep** the `[project]` section if you plan to use other PEP 621-compliant tools, or create one if it doesn't exist, defining your project name, version, etc. UV and `pip` can read dependencies from here.
    *   Your `[project]` section in `pyproject.toml` would look something like this, listing dependencies directly:
        ```toml
        [project]
        name = "alas"
        version = "0.1.0"
        requires-python = ">=3.7"
        dependencies = [
            "numpy==1.21.0",
            "opencv-python==4.5.3.56",
            # ... list all dependencies from requirements.txt here
        ]

        [project.optional-dependencies]
        dev = [
            "pytest",
            # ... list all dev dependencies here
        ]
        ```

**Phase 3: Update Scripts and Workflow**

7.  **Create and Activate a Virtual Environment:** The new workflow will require manually creating and activating a venv.
    ```bash
    # Create the virtual environment
    python -m venv .venv

    # Activate it (Windows)
    .venv\Scripts\activate
    ```
8.  **Install Dependencies with UV:** Use UV to install the packages from your new requirements file.
    ```bash
    uv pip install -r requirements.txt
    ```
9.  **Find and Replace `poetry` Commands:** Search the entire project for instances of `poetry` and replace them with the new UV/venv workflow.
    *   `poetry install` -> `uv pip install -r requirements.txt`
    *   `poetry run <command>` -> `<command>` (This assumes the virtual environment is already active). Your scripts will now need to include the venv activation step.
    *   `poetry shell` -> The concept is replaced by manually running your activation script (e.g., `.venv\Scripts\activate`).
10. **Update Scripts:** Go through every `.bat` and `.ps1` file and update them.
    *   For example, `run_alas.bat` might change from `poetry run python alas.py` to:
        ```bat
        @echo off
        CALL .\.venv\Scripts\activate.bat
        python alas.py
        ```

**Phase 4: Documentation and Cleanup**

11. **Update Documentation:**
    *   Delete `POETRY_SETUP.md`.
    *   Update `README.md`, `SETUP_GUIDE.md`, and any other developer guides to reflect the new setup process (creating a venv, activating it, running `uv pip install`).
12. **Remove Poetry Artifacts:**
    *   Delete the `poetry.lock` file. It is no longer the source of truth for locked dependencies.
13. **Test Everything:**
    *   Run every single setup script (`setup_simple.bat`, `setup_environment.bat`, etc.) to ensure they work correctly.
    *   Run the application itself (`run_alas.bat`, `run_gui.bat`) to confirm it launches and functions as expected with the new environment.
