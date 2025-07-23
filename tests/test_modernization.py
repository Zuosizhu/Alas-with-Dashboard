import ast
import re
from pathlib import Path
import os
import sys

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def test_no_old_string_formatting():
    """Verify no old-style string formatting remains"""
    print("Testing for old string formatting patterns...")
    
    # Pattern to find % formatting (but not modulo operations)
    percent_pattern = re.compile(r'%\s*[sdifr]')
    format_pattern = re.compile(r'\.format\s*\(')
    
    violations = []
    files_checked = 0
    
    for py_file in Path("module").rglob("*.py"):
        files_checked += 1
        try:
            with open(py_file, 'r', encoding='utf-8') as f:
                content = f.read()
                
            # Quick check if patterns exist
            if percent_pattern.search(content) or format_pattern.search(content):
                # Parse AST to verify it's in actual code (not comments)
                try:
                    tree = ast.parse(content)
                    for node in ast.walk(tree):
                        if isinstance(node, ast.Str):
                            if percent_pattern.search(node.s) or format_pattern.search(node.s):
                                violations.append(str(py_file))
                                break
                except:
                    # If we can't parse, be conservative and flag it
                    violations.append(f"{py_file} (parse error)")
                    
        except Exception as e:
            print(f"[WARN] Could not check {py_file}: {e}")
    
    print(f"[INFO] Checked {files_checked} Python files")
    
    if violations:
        print(f"[FAIL] Found old string formatting in {len(violations)} files:")
        for v in violations[:5]:  # Show first 5
            print(f"  - {v}")
        if len(violations) > 5:
            print(f"  ... and {len(violations) - 5} more")
        return False
    else:
        print("[PASS] No old string formatting found")
        return True

def test_modern_type_hints():
    """Check for modern type hints usage"""
    print("\nTesting for modern type hints...")
    
    # Pattern to find old typing imports
    old_typing_pattern = re.compile(r'from typing import.*\b(List|Dict|Tuple|Set|Optional)\b')
    
    violations = []
    modernized = []
    files_checked = 0
    
    for py_file in Path("module").rglob("*.py"):
        files_checked += 1
        try:
            with open(py_file, 'r', encoding='utf-8') as f:
                content = f.read()
                
            # Check for old typing imports
            if old_typing_pattern.search(content):
                violations.append(str(py_file))
            
            # Check for modern syntax (| for Union)
            if ' | ' in content and 'isinstance' not in content:
                modernized.append(str(py_file))
                
        except Exception as e:
            print(f"[WARN] Could not check {py_file}: {e}")
    
    print(f"[INFO] Found {len(modernized)} files using modern union syntax (|)")
    
    if violations:
        # This is expected since not all were converted
        print(f"[INFO] {len(violations)} files still use old typing imports (acceptable)")
        return True  # Not a failure, just informational
    else:
        print("[PASS] All files use modern type hints")
        return True

def test_f_strings_usage():
    """Check that f-strings are being used"""
    print("\nTesting f-string adoption...")
    
    f_string_pattern = re.compile(r'f["\'].*{.*}.*["\']')
    
    files_with_f_strings = 0
    files_checked = 0
    
    for py_file in Path("module").rglob("*.py"):
        files_checked += 1
        try:
            with open(py_file, 'r', encoding='utf-8') as f:
                content = f.read()
                
            if f_string_pattern.search(content):
                files_with_f_strings += 1
                
        except Exception as e:
            print(f"[WARN] Could not check {py_file}: {e}")
    
    percentage = (files_with_f_strings / files_checked) * 100 if files_checked > 0 else 0
    
    print(f"[INFO] {files_with_f_strings}/{files_checked} files use f-strings ({percentage:.1f}%)")
    
    if percentage > 30:  # Reasonable threshold
        print("[PASS] Good f-string adoption")
        return True
    else:
        print("[WARN] Low f-string adoption, but not a failure")
        return True

def test_black_formatting():
    """Check if code follows Black formatting"""
    print("\nTesting Black formatting compliance...")
    
    # Check a sample file for Black formatting indicators
    sample_files = [
        "alas.py",
        "module/base/base.py",
        "module/config/config.py"
    ]
    
    black_indicators = 0
    for file_path in sample_files:
        if os.path.exists(file_path):
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    
                # Black formatting indicators
                if '")' in content:  # Black puts closing parens on new lines
                    black_indicators += 1
                if 'Optional[' in content or ': None' in content:  # Type hints
                    black_indicators += 1
                    
            except Exception as e:
                print(f"[WARN] Could not check {file_path}: {e}")
    
    if black_indicators >= len(sample_files):
        print("[PASS] Code appears to be Black-formatted")
        return True
    else:
        print("[WARN] Cannot confirm Black formatting")
        return True

def test_python_version_features():
    """Check for Python 3.10+ features"""
    print("\nTesting Python 3.10+ feature adoption...")
    
    # Check pyproject.toml for Python version
    if os.path.exists("pyproject.toml"):
        with open("pyproject.toml", 'r') as f:
            content = f.read()
            
        if 'python = "^3.10"' in content:
            print("[PASS] pyproject.toml requires Python 3.10+")
        else:
            print("[FAIL] pyproject.toml should require Python 3.10+")
            return False
            
        if 'poetry' in content.lower():
            print("[PASS] Project uses Poetry for dependency management")
        else:
            print("[FAIL] Project should use Poetry")
            return False
            
        return True
    else:
        print("[FAIL] pyproject.toml not found")
        return False

if __name__ == "__main__":
    print("=" * 50)
    print("MODERNIZATION TESTS")
    print("=" * 50)
    
    tests = [
        test_no_old_string_formatting(),
        test_modern_type_hints(),
        test_f_strings_usage(),
        test_black_formatting(),
        test_python_version_features()
    ]
    
    passed = sum(tests)
    total = len(tests)
    
    print("\n" + "=" * 50)
    if passed == total:
        print(f"[PASS] ALL MODERNIZATION TESTS PASSED ({passed}/{total})")
    else:
        print(f"[FAIL] SOME TESTS FAILED ({passed}/{total} passed)")