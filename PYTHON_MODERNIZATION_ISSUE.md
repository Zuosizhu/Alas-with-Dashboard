# Issue: Complete Python 3.10+ Modernization

## Overview
Complete the Python modernization that was started but stashed during OCR migration work.

## Background
During the OCR migration work, we discovered that a previous agent had partially refactored the codebase but left it broken. We fixed the OCR issue but stashed the Python modernization changes to focus on getting ALAS working again.

## Tasks
- [ ] Apply stashed Python modernization changes from `modernize-with-tesseract` branch
- [ ] Update all Python code to use modern syntax:
  - [ ] Replace `%` formatting with f-strings
  - [ ] Add type hints where appropriate
  - [ ] Use pathlib instead of os.path
  - [ ] Update class definitions to modern style
  - [ ] Remove Python 2 compatibility code
- [ ] Run Black formatter on entire codebase
- [ ] Run Ruff linter and fix issues
- [ ] Update pyproject.toml with proper Python version constraint (>=3.10)
- [ ] Update requirements.txt:
  - [ ] Remove deprecated dependencies (cnocr, mxnet, gluoncv)
  - [ ] Add optional OCR dependencies (easyocr, pytesseract)
  - [ ] Update all dependencies to latest compatible versions
- [ ] Test thoroughly to ensure nothing breaks

## Related Work
- OCR Migration PR: See `modernize-with-tesseract` branch
- Original modernization plan: See `MODERNIZATION_PLAN.md` in the `modernize-with-tesseract` branch
- Stashed changes: Available in git stash on `modernize-with-tesseract` branch

## Benefits
- Cleaner, more maintainable code
- Better IDE support with type hints
- Improved performance with modern Python features
- Easier for new contributors to understand

## Technical Details
The modernization includes:
1. **Code Style**: Apply Black formatter for consistent style
2. **Linting**: Use Ruff for modern Python linting
3. **Type Hints**: Add type annotations for better IDE support
4. **Modern Syntax**: Use f-strings, walrus operator, etc.
5. **Dependencies**: Migrate to pyproject.toml from requirements.txt

## Notes
The stashed changes can be found on the `modernize-with-tesseract` branch. Care should be taken to:
1. Apply changes incrementally
2. Test each module after modernization
3. Ensure the bot still functions correctly with the game
4. Fix the logger Unicode issues on Windows

## Priority
Medium (ALAS works without this, but it would improve code quality)

## Labels
- enhancement
- technical-debt
- python