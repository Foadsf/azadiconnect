import sys
import os

def patch_environment():
    """Inject system typelib paths so AppImage can find GTK."""
    possible_paths = [
        "/usr/lib/x86_64-linux-gnu/girepository-1.0",  # Debian/Ubuntu/Mint
        "/usr/lib/girepository-1.0",                   # Arch/Generic
        "/usr/lib64/girepository-1.0",                 # Fedora/RHEL
    ]
    
    current_path = os.environ.get("GI_TYPELIB_PATH", "")
    found_paths = [p for p in possible_paths if os.path.exists(p)]
    
    if found_paths:
        # Prepend found paths to ensure they are searched
        new_path = ":".join(found_paths)
        if current_path:
            new_path += ":" + current_path
        os.environ["GI_TYPELIB_PATH"] = new_path
        # print(f"Patched GI_TYPELIB_PATH: {new_path}")

# Run patch before importing app logic
patch_environment()

from azadiconnect.app import main

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
