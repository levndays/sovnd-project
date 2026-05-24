import sys
import types
from pathlib import Path
from unittest.mock import MagicMock

_project_root = Path(__file__).parent.parent
sys.path.insert(0, str(_project_root))

_mock_docker = types.ModuleType("docker")
_mock_docker.DockerClient = MagicMock
_mock_docker.errors = types.ModuleType("docker.errors")
_mock_docker.errors.DockerException = Exception
sys.modules["docker"] = _mock_docker
sys.modules["docker.errors"] = _mock_docker.errors

import pytest

pytest_plugins = []