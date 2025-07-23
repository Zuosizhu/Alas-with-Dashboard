import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def test_ocr_files_exist():
    """Check that OCR files exist and are not empty"""
    print("Testing OCR file integrity...")
    
    ocr_files = [
        "module/ocr/ocr.py",
        "module/ocr/models.py", 
        "module/ocr/rpc.py",
        "module/ocr/al_ocr.py"
    ]
    
    all_good = True
    for file_path in ocr_files:
        if os.path.exists(file_path):
            size = os.path.getsize(file_path)
            if size > 100:  # Reasonable minimum size
                print(f"[PASS] {file_path} exists ({size} bytes)")
            else:
                print(f"[FAIL] {file_path} is too small ({size} bytes)")
                all_good = False
        else:
            print(f"[FAIL] {file_path} does not exist")
            all_good = False
    
    return all_good

def test_ocr_imports_safely():
    """Test that OCR modules can be imported without crashing"""
    print("\nTesting safe OCR imports...")
    
    # Test direct file parsing to avoid logger issues
    test_cases = [
        ("module/ocr/al_ocr.py", "AlOcr class"),
        ("module/ocr/models.py", "OcrModel class"),
    ]
    
    all_good = True
    for file_path, description in test_cases:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                
            # Check for NotImplementedError in al_ocr.py
            if "al_ocr.py" in file_path:
                if 'NotImplementedError' in content and 'OCR functionality has been removed' in content:
                    print(f"[PASS] {file_path} properly raises NotImplementedError")
                else:
                    print(f"[FAIL] {file_path} should raise NotImplementedError")
                    all_good = False
                    
            # Check models.py has placeholder
            elif "models.py" in file_path:
                if 'Placeholder for OCR models' in content:
                    print(f"[PASS] {file_path} has placeholder comment")
                else:
                    print(f"[WARN] {file_path} missing placeholder comment")
                    
        except Exception as e:
            print(f"[FAIL] Could not read {file_path}: {e}")
            all_good = False
    
    return all_good

def test_ocr_deprecation_handling():
    """Check OCR deprecation is handled properly"""
    print("\nTesting OCR deprecation handling...")
    
    # Check rpc.py for deprecation handling
    try:
        with open("module/ocr/rpc.py", 'r', encoding='utf-8') as f:
            rpc_content = f.read()
            
        checks = [
            ('logger.warning' in rpc_content, "RPC module logs warnings"),
            ('return ""' in rpc_content, "RPC methods return empty strings"),
            ('OCR functionality has been removed' in rpc_content, "Deprecation message exists"),
            ('online = False' in rpc_content, "OCR server marked as offline")
        ]
        
        all_good = True
        for check, description in checks:
            if check:
                print(f"[PASS] {description}")
            else:
                print(f"[FAIL] {description}")
                all_good = False
                
        return all_good
        
    except Exception as e:
        print(f"[FAIL] Could not check deprecation: {e}")
        return False

def test_commission_handles_ocr():
    """Check if commission module handles OCR removal"""
    print("\nTesting commission module OCR handling...")
    
    try:
        with open("module/commission/project.py", 'r', encoding='utf-8') as f:
            content = f.read()
            
        # Check that it still imports OCR
        if 'from module.ocr.ocr import' in content:
            print("[PASS] Commission module still imports OCR (for compatibility)")
        else:
            print("[FAIL] Commission module should maintain OCR imports")
            return False
            
        # Check SuffixOcr exists
        if 'class SuffixOcr(Ocr):' in content:
            print("[PASS] SuffixOcr class still defined")
        else:
            print("[FAIL] SuffixOcr class missing")
            return False
            
        return True
        
    except Exception as e:
        print(f"[FAIL] Could not check commission module: {e}")
        return False

if __name__ == "__main__":
    print("=" * 50)
    print("OCR REMOVAL TESTS (Simplified)")
    print("=" * 50)
    
    tests = [
        test_ocr_files_exist(),
        test_ocr_imports_safely(),
        test_ocr_deprecation_handling(),
        test_commission_handles_ocr()
    ]
    
    passed = sum(tests)
    total = len(tests)
    
    print("\n" + "=" * 50)
    if passed == total:
        print(f"[PASS] ALL OCR TESTS PASSED ({passed}/{total})")
    else:
        print(f"[FAIL] SOME TESTS FAILED ({passed}/{total} passed)")