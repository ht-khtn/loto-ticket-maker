#!/usr/bin/env python
"""Entrypoint cho PyInstaller - khởi động ứng dụng Loto Ticket Maker"""

import sys
sys.path.insert(0, 'src')

from loto_ticket_maker.main import main

if __name__ == "__main__":
    raise SystemExit(main())
