#!/usr/bin/env python3
"""Standalone entry point: `python mastg.py <command>`."""
import sys
from mastg_harness.cli import main

if __name__ == "__main__":
    sys.exit(main())
