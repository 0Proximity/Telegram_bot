#!/usr/bin/env python3
"""
Script to install dependencies on Render.com
"""
import subprocess
import sys

def install_dependencies():
    """Install all required dependencies"""
    dependencies = [
        "Flask==2.3.3",
        "requests==2.31.0", 
        "python-telegram-bot==20.3",
        "numpy==1.24.0",
        "APScheduler==3.10.4",
        "python-dotenv==1.0.0"
    ]
    
    print("📦 Installing dependencies...")
    
    for dep in dependencies:
        try:
            print(f"Installing {dep}...")
            subprocess.check_call([sys.executable, "-m", "pip", "install", dep])
            print(f"✅ {dep} installed successfully")
        except subprocess.CalledProcessError as e:
            print(f"❌ Failed to install {dep}: {e}")
    
    # Try optional dependencies
    optional_deps = [
        "qiskit==1.0.0",
        "qiskit-ibm-runtime==0.21.0",
        "qiskit-aer==0.12.0"
    ]
    
    print("\n🔧 Installing optional dependencies...")
    for dep in optional_deps:
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", dep])
            print(f"✅ {dep} installed")
        except:
            print(f"⚠️ {dep} not installed (optional)")

if __name__ == "__main__":
    install_dependencies()