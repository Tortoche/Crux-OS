#!/usr/bin/env python3
"""
Crux + Coucou Runtime Host
Lance l'interface officielle Coucou via le runtime Electron natif pour une transparence parfaite sous Windows.
"""

import sys
import subprocess
from pathlib import Path

def main():
    coucou_windows_dir = Path(__file__).parent.parent / "coucou-repo" / "windows"
    electron_script = coucou_windows_dir / "electron_coucou.cjs"

    try:
        proc = subprocess.run(
            ["npx", "electron", str(electron_script)],
            cwd=str(coucou_windows_dir),
            shell=True
        )
    except KeyboardInterrupt:
        pass

if __name__ == "__main__":
    main()
