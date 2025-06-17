#!/usr/bin/env python3
"""
Setup script for Lottery Stock Tracker
This script automates the initial setup process
"""

import subprocess
import sys
import os

def run_command(command, description):
    """Run a command and handle errors"""
    print(f"🔄 {description}...")
    try:
        result = subprocess.run(command, shell=True, check=True, capture_output=True, text=True)
        print(f"✅ {description} completed successfully!")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Error during {description}:")
        print(f"   {e.stderr}")
        return False

def main():
    print("🎫 Lottery Stock Tracker - Setup Script")
    print("=" * 50)
    
    # Check if we're in a virtual environment
    if not hasattr(sys, 'real_prefix') and not (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix):
        print("⚠️  Warning: You don't appear to be in a virtual environment.")
        response = input("Do you want to continue anyway? (y/N): ")
        if response.lower() != 'y':
            print("Setup cancelled. Please create and activate a virtual environment first:")
            print("  python -m venv lottery-env")
            print("  lottery-env\\Scripts\\activate  # Windows")
            print("  source lottery-env/bin/activate  # macOS/Linux")
            return
    
    # Install dependencies
    if not run_command("pip install -r requirements.txt", "Installing dependencies"):
        return
    
    # Initialize database
    if not run_command("flask init-db", "Initializing database"):
        return
    
    print("\n🎉 Setup completed successfully!")
    print("\nTo start the application:")
    print("  python app.py")
    print("\nThen open your browser to: http://localhost:5000")

if __name__ == "__main__":
    main() 