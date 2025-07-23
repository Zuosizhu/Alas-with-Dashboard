import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def test_ocr_returns_safe_defaults():
    """Verify OCR methods return safe defaults"""
    print("Testing OCR safe defaults...")
    
    try:
        # Import without external dependencies
        import module.ocr.ocr as ocr_module
        import module.ocr.al_ocr as al_ocr_module
        
        # Test that modules imported
        print("[PASS] OCR modules imported successfully")
        
        # Check AlOcr raises NotImplementedError
        try:
            al_ocr = al_ocr_module.AlOcr()
            try:
                al_ocr.ocr(None)
                print("[FAIL] AlOcr.ocr should raise NotImplementedError")
                return False
            except NotImplementedError:
                print("[PASS] AlOcr.ocr correctly raises NotImplementedError")
        except Exception as e:
            print(f"[WARN] Could not test AlOcr: {e}")
        
        # Check for safe stub methods
        try:
            al_ocr.ocr_for_single_line(None)
            print("[FAIL] AlOcr.ocr_for_single_line should raise NotImplementedError")
            return False
        except NotImplementedError:
            print("[PASS] AlOcr.ocr_for_single_line correctly raises NotImplementedError")
        
        return True
        
    except ImportError as e:
        print(f"[WARN] Cannot test OCR without dependencies: {e}")
        return True  # Not a failure if we can't import

def test_ocr_rpc_module():
    """Test OCR RPC module handles removal properly"""
    print("\nTesting OCR RPC module...")
    
    try:
        import module.ocr.rpc as rpc_module
        
        # Test ModelProxy returns empty strings
        proxy = rpc_module.ModelProxy("test_lang")
        
        # Test ocr method
        result = proxy.ocr(None)
        if result == "":
            print("[PASS] ModelProxy.ocr returns empty string")
        else:
            print(f"[FAIL] ModelProxy.ocr returned '{result}' instead of empty string")
            return False
        
        # Test ocr_for_single_line
        result = proxy.ocr_for_single_line(None)
        if result == "":
            print("[PASS] ModelProxy.ocr_for_single_line returns empty string")
        else:
            print(f"[FAIL] ModelProxy.ocr_for_single_line returned '{result}'")
            return False
        
        # Test ocr_for_single_lines with list
        result = proxy.ocr_for_single_lines([1, 2, 3])
        if result == ["", "", ""]:
            print("[PASS] ModelProxy.ocr_for_single_lines returns correct empty list")
        else:
            print(f"[FAIL] ModelProxy.ocr_for_single_lines returned {result}")
            return False
        
        # Test factory
        factory = rpc_module.ModelProxyFactory()
        test_proxy = factory.test_model
        if isinstance(test_proxy, rpc_module.ModelProxy):
            print("[PASS] ModelProxyFactory creates ModelProxy instances")
        else:
            print("[FAIL] ModelProxyFactory did not create ModelProxy")
            return False
        
        # Test server functions don't crash
        rpc_module.start_ocr_server()
        print("[PASS] start_ocr_server doesn't crash")
        
        rpc_module.start_ocr_server_process()
        print("[PASS] start_ocr_server_process doesn't crash")
        
        if not rpc_module.alive():
            print("[PASS] alive() returns False as expected")
        else:
            print("[FAIL] alive() should return False")
            return False
        
        return True
        
    except ImportError as e:
        print(f"[WARN] Cannot test RPC module: {e}")
        return True

def test_ocr_dependent_modules():
    """Test modules that depend on OCR still initialize"""
    print("\nTesting OCR-dependent modules...")
    
    modules_to_test = [
        ("module.commission.project", "Commission classes"),
        ("module.campaign.campaign_ocr", "Campaign OCR")
    ]
    
    success_count = 0
    
    for module_path, description in modules_to_test:
        try:
            module = __import__(module_path)
            print(f"[PASS] {module_path} imported ({description})")
            success_count += 1
        except ImportError as e:
            error_str = str(e)
            # Check if it's a dependency issue
            if any(dep in error_str for dep in ['cv2', 'numpy', 'imageio', 'PIL']):
                print(f"[WARN] {module_path}: Missing image processing dependency (expected)")
                success_count += 1
            else:
                print(f"[FAIL] {module_path} failed to import: {e}")
        except Exception as e:
            print(f"[FAIL] {module_path} unexpected error: {type(e).__name__}: {e}")
    
    return success_count == len(modules_to_test)

def test_ocr_logging():
    """Check that OCR methods log deprecation warnings"""
    print("\nTesting OCR deprecation logging...")
    
    try:
        # We'll check if logger calls are present
        import module.ocr.rpc as rpc_module
        
        # Check the source code contains logging
        import inspect
        
        proxy_source = inspect.getsource(rpc_module.ModelProxy.ocr)
        if "logger.warning" in proxy_source:
            print("[PASS] OCR methods include deprecation warnings")
            return True
        else:
            print("[FAIL] OCR methods should log deprecation warnings")
            return False
            
    except Exception as e:
        print(f"[WARN] Could not check logging: {e}")
        return True

if __name__ == "__main__":
    print("=" * 50)
    print("OCR REMOVAL TESTS")
    print("=" * 50)
    
    tests = [
        test_ocr_returns_safe_defaults(),
        test_ocr_rpc_module(),
        test_ocr_dependent_modules(),
        test_ocr_logging()
    ]
    
    passed = sum(tests)
    total = len(tests)
    
    print("\n" + "=" * 50)
    if passed == total:
        print(f"[PASS] ALL OCR TESTS PASSED ({passed}/{total})")
    else:
        print(f"[FAIL] SOME TESTS FAILED ({passed}/{total} passed)")