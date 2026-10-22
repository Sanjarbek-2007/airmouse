"""PyInstaller entry point (the package's own __main__ uses relative imports)."""
from aircursor.cli import main

if __name__ == "__main__":
    raise SystemExit(main())
