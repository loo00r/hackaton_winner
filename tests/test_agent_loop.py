import os
import sys

from pathlib import Path


_THIS_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_THIS_DIR))
print(_THIS_DIR)

from src.agent.loop import agent_loop

def test_agent_loop():
    assert True