#!/usr/bin/env python3
"""AI TransMate — Terminal translation tool with LLM-powered language detection.

Usage: python main.py   or   python -m transmate
"""

import sys


def _enable_vt():
    if sys.platform != "win32":
        return
    try:
        sys.stdout.reconfigure(virtual_terminal_processing=True)
    except Exception:
        pass


def main():
    _enable_vt()
    from transmate.cli import TransMateCLI
    TransMateCLI().run()


if __name__ == "__main__":
    main()
