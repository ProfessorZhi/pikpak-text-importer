import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "app"))

from pikpak_importer.gui import gui_main


if __name__ == "__main__":
    raise SystemExit(gui_main())
