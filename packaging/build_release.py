import shutil
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DIST_DIR = ROOT / "dist"
BUILD_DIR = ROOT / "build"
APP_DIST_DIR = DIST_DIR / "app"
INSTALLER_DIST_DIR = DIST_DIR / "installer"
APP_NAME = "PikPakTextImporter"


def run(command: list[str], *, cwd: Path | None = None) -> None:
    print(">", " ".join(command))
    subprocess.run(command, cwd=cwd or ROOT, check=True)


def find_iscc() -> str | None:
    candidates = [
        shutil.which("iscc"),
        str(Path.home() / "AppData" / "Local" / "Programs" / "Inno Setup 6" / "ISCC.exe"),
        r"C:\Program Files\Inno Setup 6\ISCC.exe",
        r"C:\Program Files (x86)\Inno Setup 6\ISCC.exe",
    ]
    for candidate in candidates:
        if candidate and Path(candidate).exists():
            return candidate
    return None


def main() -> int:
    pyinstaller = shutil.which("pyinstaller")
    if not pyinstaller:
        print("PyInstaller not found. Please install it first.", file=sys.stderr)
        return 1

    iscc = find_iscc()
    if not iscc:
        print("Inno Setup compiler not found. Please install Inno Setup first.", file=sys.stderr)
        return 1

    if DIST_DIR.exists():
        shutil.rmtree(DIST_DIR)
    if BUILD_DIR.exists():
        shutil.rmtree(BUILD_DIR)

    APP_DIST_DIR.mkdir(parents=True, exist_ok=True)
    INSTALLER_DIST_DIR.mkdir(parents=True, exist_ok=True)

    run(
        [
            pyinstaller,
            "--noconfirm",
            "--clean",
            "--windowed",
            "--onedir",
            "--name",
            APP_NAME,
            "--distpath",
            str(APP_DIST_DIR),
            "--workpath",
            str(BUILD_DIR / "pyinstaller"),
            "--specpath",
            str(BUILD_DIR / "spec"),
            "--paths",
            str(ROOT / "app"),
            "--add-data",
            f"{ROOT / 'assets'};assets",
            "--hidden-import",
            "pikpakapi",
            str(ROOT / "scripts" / "run_gui.py"),
        ]
    )

    run(
        [
            iscc,
            str(ROOT / "packaging" / "PikPakTextImporter.iss"),
        ]
    )

    print()
    print("Build completed:")
    print(f"- App folder: {APP_DIST_DIR / APP_NAME}")
    print(f"- Installer: {INSTALLER_DIST_DIR / (APP_NAME + '-Setup.exe')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
