# -*- coding: utf-8 -*-
"""
Poseidon Player - Background Service
Handles keep-alive for streams and reminder notifications
"""

import sys
import os

# Add addon path to sys.path for imports
addon_path = os.path.dirname(os.path.abspath(__file__))
if addon_path not in sys.path:
    sys.path.insert(0, addon_path)

from main import run_background_service

if __name__ == '__main__':
    run_background_service()
