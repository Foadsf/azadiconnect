from azadiconnect.app import main

import sys

if __name__ == "__main__":
    try:
        main().main_loop()
    except ValueError as e:
        if "Namespace Gdk not available" in str(e):
            print("""
CRITICAL ERROR: Missing System Dependencies

AzadiConnect requires GTK system libraries to run.
Please install them using your package manager:

Ubuntu/Debian/Mint:
  sudo apt install gir1.2-gtk-3.0 libgirepository-1.0-1

Fedora:
  sudo dnf install gtk3 gobject-introspection

Arch:
  sudo pacman -S gtk3 gobject-introspection
""")
            sys.exit(1)
        raise e
