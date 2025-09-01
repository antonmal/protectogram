#!/usr/bin/env python3.11
import sys
import importlib

def check_package(name, required_version=None):
    try:
        module = importlib.import_module(name.split('[')[0])
        version = getattr(module, '__version__', 'unknown')
        status = "✓"
        if required_version and version != required_version:
            status = f"⚠️  (got {version}, expected {required_version})"
        print(f"{name:30} {version:10} {status}")
        return True
    except ImportError as e:
        print(f"{name:30} {'MISSING':10} ❌ - {e}")
        return False

print(f"Python Version: {sys.version}")
print(f"Python Path: {sys.executable}")
print("\n" + "="*50)
print("Package Verification:")
print("="*50)

packages = [
    ("fastapi", "0.115.0"),
    ("pydantic", "2.9.2"),
    ("sqlalchemy", "2.0.35"),
    ("celery", "5.4.0"),
    ("redis", "5.2.0"),
    ("telegram", "21.6"),
    ("twilio", None),
    ("asyncpg", None),
    ("alembic", None),
]

all_ok = all(check_package(pkg, ver) for pkg, ver in packages)

if all_ok:
    print("\n✅ All packages installed correctly!")
else:
    print("\n❌ Some packages are missing or have wrong versions")
    sys.exit(1)