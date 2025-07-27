import sys
import os

def resource_path(relative_path):
    """
    Get the absolute path to a resource, which works for both development
    (running from source) and for a PyInstaller bundle.
    """
    try:
        # PyInstaller creates a temp folder and stores its path in _MEIPASS.
        base_path = sys._MEIPASS
    except Exception:
        # Not running in a bundle, so the base path is the project's root.
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)