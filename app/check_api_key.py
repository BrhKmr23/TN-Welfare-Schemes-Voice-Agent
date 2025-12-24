"""Quick script to verify GOOGLE_API_KEY is set correctly."""

import os
import sys
import io

# Fix Windows console encoding
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

def check_api_key():
    """Check if GOOGLE_API_KEY is set and valid."""
    api_key = os.getenv("GOOGLE_API_KEY")
    
    if not api_key:
        print("[ERROR] GOOGLE_API_KEY is not set!")
        print("\nTo set it:")
        print("  Windows PowerShell:")
        print("    $env:GOOGLE_API_KEY='YOUR_KEY'")
        print("    # Note: Use $env: not 'set' in PowerShell")
        print("\n  Windows Command Prompt (CMD):")
        print("    set GOOGLE_API_KEY=YOUR_KEY")
        print("\n  Linux/Mac:")
        print("    export GOOGLE_API_KEY=YOUR_KEY")
        print("\n  To make it persistent in PowerShell, add to your profile:")
        print("    [System.Environment]::SetEnvironmentVariable('GOOGLE_API_KEY', 'YOUR_KEY', 'User')")
        return False
    
    if len(api_key) < 20:
        print(f"[WARNING] API key seems too short ({len(api_key)} chars). It might be invalid.")
        return False
    
    print(f"[OK] GOOGLE_API_KEY is set (length: {len(api_key)} chars)")
    print(f"     First 10 chars: {api_key[:10]}...")
    
    # Try to import and test
    try:
        from google import genai
        client = genai.Client(api_key=api_key)
        print("[OK] Gemini client created successfully")
        return True
    except ImportError:
        print("[WARNING] google-genai package not installed. Run: pip install google-genai")
        return False
    except Exception as e:
        print(f"[ERROR] Failed to create Gemini client: {e}")
        print("        The API key might be invalid.")
        return False

if __name__ == "__main__":
    success = check_api_key()
    sys.exit(0 if success else 1)

