"""Allow running as: python -m transmate"""
import sys

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(virtual_terminal_processing=True)
    except Exception:
        pass

from .cli import TransMateCLI


def main():
    TransMateCLI().run()


if __name__ == "__main__":
    main()
