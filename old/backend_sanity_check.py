"""
backend_sanity_check.py
Verifies structure, dependencies, and versions for your AI Agent FastAPI backend.
"""

import os
import sys
import subprocess
from pathlib import Path
from typing import List

print("\n🧠 Running Backend AI Agent Sanity Check...\n")

# --- Auto-detect backend root ---
cwd = Path(__file__).resolve().parent
backend_root = cwd / "backend"
if not backend_root.exists():
    # try walking upward until "backend" is found
    for parent in cwd.parents:
        candidate = parent / "backend"
        if candidate.exists():
            backend_root = candidate
            break

if not backend_root.exists():
    print("❌ Could not locate backend directory.")
    sys.exit(1)

print(f"📁 Detected backend root: {backend_root}\n")

# --- Required directories & files ---
required_dirs: List[str] = [
    "agents",
    "common",
]

required_files: List[str] = [
    "main.py",
    ".env",
    "requirements.txt",
]

# --- Check directories ---
for d in required_dirs:
    dir_path = backend_root / d
    if dir_path.exists():
        print(f"✅ Found directory: {d}")
    else:
        print(f"⚠️ Missing directory: {d}")

# --- Check files ---
for f in required_files:
    file_path = backend_root / f
    if file_path.exists():
        print(f"✅ Found file: {f}")
    else:
        print(f"⚠️ Missing file: {f}")

# --- Check dependencies from requirements.txt ---
req_file = backend_root / "requirements.txt"
if req_file.exists():
    print("\n📦 Checking Python dependencies...\n")
    with open(req_file) as f:
        lines = [line.strip() for line in f if line.strip() and not line.startswith("#")]
    required_pkgs = ["fastapi", "uvicorn", "pydantic", "requests"]
    for pkg in required_pkgs:
        if any(pkg.lower() in line.lower() for line in lines):
            print(f"✅ {pkg} listed in requirements.txt")
        else:
            print(f"⚠️ {pkg} missing from requirements.txt")
else:
    print("\n⚠️ requirements.txt not found. Skipping dependency list check.")

# --- Check installed Python packages ---
print("\n🧩 Checking installed package versions...\n")
required_installed = ["fastapi", "uvicorn", "pydantic", "requests"]
for pkg in required_installed:
    try:
        result = subprocess.check_output([sys.executable, "-m", "pip", "show", pkg], text=True)
        version = next((line.split(":")[1].strip() for line in result.splitlines() if line.startswith("Version:")), None)
        print(f"✅ {pkg} v{version}")
    except subprocess.CalledProcessError:
        print(f"❌ {pkg} not installed")

# --- Python & pip version ---
try:
    python_ver = subprocess.check_output([sys.executable, "--version"], text=True).strip()
    pip_ver = subprocess.check_output([sys.executable, "-m", "pip", "--version"], text=True).strip()
    print(f"\n🧩 {python_ver}")
    print(f"🧩 {pip_ver}")
except Exception as e:
    print(f"⚠️ Could not check Python/pip versions: {e}")

print("\n✅ Backend Sanity Check Complete.\n")
