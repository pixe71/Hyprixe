#!/usr/bin/python3
"""Compatibility entry point for the protocol in the Hyprixe Core checkout."""

from pathlib import Path
from runpy import run_path

if __name__ == '__main__':
    run_path(str(Path(__file__).resolve().parents[3] / 'common/sddm/sddm_sync.py'),
             run_name='__main__')
