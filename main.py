#!/usr/bin/env python3
"""AI TransMate — Terminal translation tool with LLM-powered language detection.

Usage: python main.py   or   python -m transmate
"""

from transmate.cli import TransMateCLI


def main():
    TransMateCLI().run()


if __name__ == "__main__":
    main()
