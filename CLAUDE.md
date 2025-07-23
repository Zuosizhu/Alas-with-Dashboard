# ALAS Development Plan

## Current Status
- **Branch**: `modernize-with-tesseract` (ready to merge)
- **OCR**: Fixed and working with flexible backend system
- **Python**: Still needs modernization (changes are stashed)

## Post-Merge Action Plan

### 1. Apply Python Modernization
**Priority: High**
- Apply stashed Python modernization changes from `modernize-with-tesseract` branch
- Run Black formatter on entire codebase for consistent style
- Run Ruff linter and fix all issues
- Update code to Python 3.10+ syntax:
  - Replace `%` formatting with f-strings
  - Add type hints where beneficial
  - Use pathlib instead of os.path
  - Remove Python 2 compatibility code
- Fix logger Unicode issues on Windows

### 2. Update Dependencies
**Priority: High**
- Remove from requirements.txt:
  - cnocr==1.2.2
  - mxnet==1.6.0
  - gluoncv
- Add as optional dependencies:
  - easyocr>=1.7.0  # For best game text recognition
  - pytesseract>=0.3.10  # For Tesseract OCR
- Update other dependencies to latest compatible versions

### 3. Install OCR Backend (User Choice)
**Priority: Medium**
- **Option A - EasyOCR** (Recommended):
  ```bash
  pip install easyocr
  ```
  - Best accuracy for game text
  - ~250MB download
  - Automatic language detection

- **Option B - Tesseract**:
  - Download: https://github.com/UB-Mannheim/tesseract/wiki
  - Install to: C:\Program Files\Tesseract-OCR
  - Add to PATH
  - Already have pytesseract installed

- **Option C - No OCR**:
  - ALAS will run with SimpleOCR placeholder
  - Returns empty strings for all OCR

### 4. Test with Actual Game
**Priority: Medium**
- Verify OCR works for:
  - Stage selection (e.g., "STAGE 3-4")
  - Timer displays (e.g., "10:30:45")
  - Resource counts
  - Commission status
  - Menu navigation
- Compare accuracy between OCR backends
- Document any issues for specific text types

### 5. Add Testing
**Priority: Low**
- Create unit tests for OCR backends
- Add integration tests with game screenshots
- Set up performance benchmarks
- Test edge cases (empty images, wrong formats)

### 6. Future Enhancements
**Priority: Low**
- Implement vision model approach (see VISION_MODEL_OCR_PROPOSAL.md)
- Add OCR result caching
- Create GUI for OCR backend selection
- Add OCR accuracy metrics/logging
- Build automated testing framework

## Clean Up Tasks
- Delete test files: `test_ocr.py`, `test_ocr_simple.py`
- Remove `PYTHON_MODERNIZATION_ISSUE.md` after creating GitHub issue
- Archive old OCR documentation

## Important Notes
- The Python modernization is tracked in a GitHub issue (see PYTHON_MODERNIZATION_ISSUE.md)
- OCR will work without any backend installed (returns empty strings)
- All changes maintain backward compatibility
- The stashed modernization changes are significant - apply carefully

## Commands Reference
```bash
# To see stashed changes
git stash list

# To apply stashed Python modernization
git stash pop

# To run Black formatter
black .

# To run Ruff linter
ruff check . --fix

# To test OCR
python test_ocr_simple.py
```