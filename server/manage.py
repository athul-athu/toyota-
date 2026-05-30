#!/usr/bin/env python
"""Django's command-line utility for administrative tasks."""
import os
import sys
from pathlib import Path


def _bootstrap_venv() -> None:
    """Re-run with server/.venv when deps are installed there (avoids 'No module named django')."""
    if os.environ.get("TOYOTA_VENV_BOOTSTRAPPED"):
        return

    base_dir = Path(__file__).resolve().parent
    if sys.platform == "win32":
        venv_python = base_dir / ".venv" / "Scripts" / "python.exe"
    else:
        venv_python = base_dir / ".venv" / "bin" / "python"

    if not venv_python.is_file():
        return

    try:
        if Path(sys.executable).resolve() == venv_python.resolve():
            return
    except OSError:
        return

    os.environ["TOYOTA_VENV_BOOTSTRAPPED"] = "1"
    os.execv(str(venv_python), [str(venv_python), *sys.argv])


def main():
    """Run administrative tasks."""
    _bootstrap_venv()
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'server.settings')
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?"
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == '__main__':
    main()
