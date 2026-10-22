"""Build a self-contained AirCursor download (no Python needed by the user).

    pip install -r requirements.txt pyinstaller
    python packaging/build.py            # -> dist/AirCursor-<version>-<os>-<arch>.tar.gz / .zip

Needs a Python with a shared libpython (python.org, uv, pyenv --enable-shared; Debian/Ubuntu system Python lacks it).
"""
from __future__ import annotations

import os
import platform
import shutil
import subprocess
import sys
import tarfile
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from aircursor import __version__  # noqa: E402
from aircursor.models import ensure_model  # noqa: E402

# Big packages the app never imports but that get pulled in by transitive dependencies.
EXCLUDES = ["tkinter", "scipy", "pandas", "IPython", "jax", "jaxlib", "torch", "tensorflow",
            "PySide6.QtQml", "PySide6.QtQuick", "PySide6.QtPdf", "PySide6.QtOpenGL"]


def main() -> int:
    system = {"Linux": "linux", "Windows": "windows", "Darwin": "macos"}[platform.system()]
    arch = platform.machine().lower().replace("amd64", "x86_64").replace("arm64", "aarch64")
    name = f"AirCursor-{__version__}-{system}-{arch}"
    build, out = ROOT / "build", ROOT / "dist"
    shutil.rmtree(build, ignore_errors=True)
    shutil.rmtree(out / "aircursor", ignore_errors=True)

    model = ensure_model()                                    # bundle the hand model: works offline on first run
    sep = os.pathsep
    cmd = [sys.executable, "-m", "PyInstaller", "--noconfirm", "--clean", "--name", "aircursor", "--onedir",
           "--distpath", str(out), "--workpath", str(build), "--specpath", str(build),
           "--paths", str(ROOT), "--collect-data", "mediapipe", "--collect-binaries", "mediapipe",
           "--add-data", f"{model}{sep}models"]
    if (ROOT / "vendor" / "lib").is_dir() and any((ROOT / "vendor" / "lib").iterdir()):
        cmd += ["--add-data", f"{ROOT / 'vendor' / 'lib'}{sep}vendor/lib"]
    for mod in EXCLUDES:
        cmd += ["--exclude-module", mod]
    cmd.append(str(ROOT / "packaging" / "launcher.py"))
    subprocess.run(cmd, check=True)

    app = out / "aircursor"
    extras = ROOT / "packaging" / system
    if extras.is_dir():                                        # installer / helper scripts for this OS
        for f in extras.iterdir():
            shutil.copy2(f, app / f.name)
    shutil.copy2(ROOT.parent / "LICENSE", app / "LICENSE")
    shutil.copy2(ROOT / "packaging" / "README.txt", app / "README.txt")

    top = out / name
    shutil.rmtree(top, ignore_errors=True)
    app.rename(top)
    if system == "windows":
        archive = out / f"{name}.zip"
        with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as z:
            for p in top.rglob("*"):
                z.write(p, p.relative_to(out))
    else:
        archive = out / f"{name}.tar.gz"
        with tarfile.open(archive, "w:gz") as t:
            t.add(top, arcname=name)
    print(f"\nbuilt {archive}  ({archive.stat().st_size / 1e6:.0f} MB)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
