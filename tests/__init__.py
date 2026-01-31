"""
Test Suite for MEP Digital Twin

This module contains tests for:
- Physics calculations (test_physics.py)
- Validation logic (test_validators.py)
- Health scoring (test_health_score.py)
- API endpoints (test_api.py)

Run tests with:
    pytest tests/ -v
    pytest tests/ --cov=core --cov=api
"""

import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
