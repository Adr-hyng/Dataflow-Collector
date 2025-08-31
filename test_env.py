#!/usr/bin/env python3
"""
Simple test script to debug .env file loading
"""

import os
from pathlib import Path

print("🔍 Testing .env file loading...")
print(f"Current working directory: {os.getcwd()}")
print(f"Script location: {Path(__file__).parent}")

# Check if .env file exists
env_path = Path('.env')
print(f"🔍 .env file exists: {env_path.exists()}")
print(f"🔍 .env file path: {env_path.absolute()}")

if env_path.exists():
    print("📄 .env file contents:")
    with open(env_path, 'r') as f:
        for i, line in enumerate(f, 1):
            print(f"  {i}: {repr(line.strip())}")

# Try to load with python-dotenv
try:
    from dotenv import load_dotenv
    print("✅ python-dotenv imported successfully")
    
    # Load .env file
    load_dotenv()
    print("✅ load_dotenv() called")
    
    # Check environment variables
    api_key = os.getenv('ROBOFLOW_API_KEY')
    if api_key:
        print(f"🔑 API Key found: {api_key[:8]}...{api_key[-4:]}")
    else:
        print("⚠️  API Key not found")
        
    # List all environment variables that contain 'ROBOFLOW'
    roboflow_vars = {k: v for k, v in os.environ.items() if 'ROBOFLOW' in k.upper()}
    print(f"🔍 Roboflow environment variables: {roboflow_vars}")
    
except ImportError as e:
    print(f"❌ python-dotenv import failed: {e}")
except Exception as e:
    print(f"❌ Error loading .env: {e}")
