import os
import pytest


@pytest.fixture
def file_path() -> str:
    """Provide a default audio file path for tests."""
    # Prefer the project's included test file if present
    candidate = os.path.join(os.path.dirname(__file__), "audio_data", "test.wav")
    if os.path.exists(candidate):
        return candidate
    # Fallback to current working directory path
    return os.path.join(os.getcwd(), "audio_data", "test.wav")
