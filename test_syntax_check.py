#!/usr/bin/env python3
"""
Simple syntax check for the observability integration.
"""
import ast
import sys

def check_syntax(filename):
    """Check if a Python file has valid syntax."""
    try:
        with open(filename, 'r') as f:
            source = f.read()
        
        # Parse the AST to check syntax
        ast.parse(source)
        print(f"✓ {filename}: Syntax OK")
        return True
    except SyntaxError as e:
        print(f"✗ {filename}: Syntax Error - {e}")
        return False
    except Exception as e:
        print(f"✗ {filename}: Error - {e}")
        return False

def check_method_signatures():
    """Check that our method signatures are correct."""
    try:
        with open('goldenverba/verba_manager.py', 'r') as f:
            content = f.read()
        
        # Check retrieve_chunks signature
        if 'user_session_id: str = None' in content:
            print("✓ retrieve_chunks: user_session_id parameter added")
        else:
            print("✗ retrieve_chunks: user_session_id parameter missing")
            return False
        
        # Check generate_stream_answer signature  
        if 'async def generate_stream_answer(' in content and 'user_session_id: str = None' in content:
            print("✓ generate_stream_answer: user_session_id parameter added")
        else:
            print("✗ generate_stream_answer: user_session_id parameter missing")
            return False
        
        # Check tracing imports
        if 'from goldenverba.observability import get_tracer' in content:
            print("✓ Observability imports added")
        else:
            print("✗ Observability imports missing")
            return False
        
        # Check span creation
        if 'tracer.start_as_current_span("rag.query")' in content:
            print("✓ RAG query span creation added")
        else:
            print("✗ RAG query span creation missing")
            return False
        
        if 'tracer.start_as_current_span("rag.generate")' in content:
            print("✓ RAG generate span creation added")
        else:
            print("✗ RAG generate span creation missing")
            return False
        
        return True
        
    except Exception as e:
        print(f"✗ Method signature check failed: {e}")
        return False

def check_api_updates():
    """Check that API endpoints were updated."""
    try:
        with open('goldenverba/server/api.py', 'r') as f:
            content = f.read()
        
        # Check query endpoint
        if 'user_session_id=payload.session_id' in content:
            print("✓ Query API endpoint updated with session_id")
        else:
            print("✗ Query API endpoint missing session_id")
            return False
        
        # Check WebSocket endpoint
        if 'user_session_id=payload.session_id' in content:
            print("✓ WebSocket endpoint updated with session_id")
        else:
            print("✗ WebSocket endpoint missing session_id")
            return False
        
        return True
        
    except Exception as e:
        print(f"✗ API update check failed: {e}")
        return False

def check_types_updates():
    """Check that type definitions were updated."""
    try:
        with open('goldenverba/server/types.py', 'r') as f:
            content = f.read()
        
        # Check QueryPayload
        if 'session_id: Optional[str] = None' in content:
            print("✓ QueryPayload updated with session_id")
        else:
            print("✗ QueryPayload missing session_id")
            return False
        
        # Check GeneratePayload
        query_count = content.count('session_id: Optional[str] = None')
        if query_count >= 2:
            print("✓ GeneratePayload updated with session_id")
        else:
            print("✗ GeneratePayload missing session_id")
            return False
        
        # Check Optional import
        if 'from typing import Literal, Optional' in content:
            print("✓ Optional import added")
        else:
            print("✗ Optional import missing")
            return False
        
        return True
        
    except Exception as e:
        print(f"✗ Types update check failed: {e}")
        return False

def main():
    """Run all checks."""
    print("Running syntax and integration checks...\n")
    
    files_to_check = [
        'goldenverba/verba_manager.py',
        'goldenverba/server/api.py', 
        'goldenverba/server/types.py',
        'goldenverba/observability.py'
    ]
    
    # Check syntax
    syntax_ok = True
    for filename in files_to_check:
        if not check_syntax(filename):
            syntax_ok = False
    
    print()
    
    if not syntax_ok:
        print("❌ Syntax errors found, stopping checks")
        return 1
    
    # Check integration
    checks = [
        check_method_signatures,
        check_api_updates,
        check_types_updates
    ]
    
    passed = 0
    total = len(checks)
    
    for check in checks:
        if check():
            passed += 1
        print()
    
    print(f"Results: {passed}/{total} integration checks passed")
    
    if passed == total:
        print("🎉 All checks passed!")
        return 0
    else:
        print("❌ Some checks failed")
        return 1

if __name__ == "__main__":
    sys.exit(main())