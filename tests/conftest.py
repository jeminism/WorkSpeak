import os
import sys
import pytest

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ['LLM_API_KEY'] = 'test_key'
os.environ['LLM_ENDPOINT'] = 'https://mock.example.com/v1/chat/completions'
