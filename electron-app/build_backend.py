#!/usr/bin/env python3
"""
Build script for Echo Desktop Backend
Bundles Python backend into a standalone executable using PyInstaller
"""

import os
import sys
import subprocess
import shutil
from pathlib import Path

# Directories
SCRIPT_DIR = Path(__file__).parent.absolute()
PROJECT_ROOT = SCRIPT_DIR.parent
ELECTRON_APP = SCRIPT_DIR
BACKEND_DIR = ELECTRON_APP / "backend"
DIST_DIR = ELECTRON_APP / "dist"
BACKEND_DIST = DIST_DIR / "backend"

def check_pyinstaller():
    """Ensure PyInstaller is installed"""
    try:
        import PyInstaller
        print(f"✓ PyInstaller {PyInstaller.__version__} found")
    except ImportError:
        print("❌ PyInstaller not found!")
        print("   Please run: uv add pyinstaller")
        sys.exit(1)

def build_backend():
    """Build the Python backend using PyInstaller"""
    print("\n" + "="*60)
    print("Building Echo Backend with PyInstaller")
    print("="*60 + "\n")
    
    # Entry point
    entry_point = BACKEND_DIR / "electron_bridge.py"
    
    if not entry_point.exists():
        print(f"❌ Entry point not found: {entry_point}")
        sys.exit(1)
    
    # PyInstaller command
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--onefile",                          # Single executable
        "--name", "echo_backend",             # Output name
        "--distpath", str(BACKEND_DIST),      # Output directory
        "--workpath", str(DIST_DIR / "build"),
        "--specpath", str(ELECTRON_APP),
        
        # Add source directories as data
        "--add-data", f"{PROJECT_ROOT / 'src'};src",
        "--add-data", f"{PROJECT_ROOT / 'system-diagnosis-mcp'};system-diagnosis-mcp",
        "--add-data", f"{PROJECT_ROOT / 'Prompts'};Prompts",
        
        # Hidden imports (modules that PyInstaller might miss)
        "--hidden-import", "src.agent",
        "--hidden-import", "src.agent.llm_agent",
        "--hidden-import", "src.agent.live_client",
        "--hidden-import", "src.agent.planner_agent",
        "--hidden-import", "src.utils",
        "--hidden-import", "google.genai",
        "--hidden-import", "langchain",
        "--hidden-import", "langchain_core",
        "--hidden-import", "langchain_google_genai",
        "--hidden-import", "mcp",
        "--hidden-import", "httpx",
        "--hidden-import", "dotenv",
        "--hidden-import", "rich",
        "--hidden-import", "textual",
        "--hidden-import", "pyaudio",
        "--hidden-import", "numpy",
        
        # Exclude unnecessary modules to reduce size
        "--exclude-module", "matplotlib",
        "--exclude-module", "PIL",
        "--exclude-module", "cv2",
        "--exclude-module", "tkinter",
        "--exclude-module", "pandas",
        "--exclude-module", "scipy",
        "--exclude-module", "ipython",
        "--exclude-module", "notebook",

        
        # Console app (for debugging, can change to --windowed later)
        "--console",
        
        # Clean build
        "--clean",
        "--noconfirm",
        
        # Entry point
        str(entry_point)
    ]
    
    print("Running PyInstaller with command:")
    print(" ".join(cmd[:10]) + " ...")
    
    # Run from project root so imports work
    result = subprocess.run(
        cmd,
        cwd=str(PROJECT_ROOT),
        capture_output=False
    )
    
    if result.returncode != 0:
        print("\n❌ PyInstaller build failed!")
        sys.exit(1)
    
    # Verify output
    if sys.platform == "win32":
        output_exe = BACKEND_DIST / "echo_backend.exe"
    else:
        output_exe = BACKEND_DIST / "echo_backend"
    
    if output_exe.exists():
        size_mb = output_exe.stat().st_size / (1024 * 1024)
        print(f"\n✅ Backend built successfully!")
        print(f"   Output: {output_exe}")
        print(f"   Size: {size_mb:.1f} MB")
    else:
        print(f"\n❌ Expected output not found: {output_exe}")
        sys.exit(1)

def copy_env_example():
    """Copy .env.example to dist for user configuration"""
    env_example = PROJECT_ROOT / ".env.example"
    if env_example.exists():
        shutil.copy(env_example, BACKEND_DIST / ".env.example")
        print("✓ Copied .env.example for user configuration")

if __name__ == "__main__":
    check_pyinstaller()
    build_backend()
    copy_env_example()
    print("\n🎉 Backend build complete! Run 'npm run build' for Electron packaging.")
