import json
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "scripts"))


@pytest.fixture
def fixture():
    def load(name: str):
        return json.loads((HERE / "fixtures" / name).read_text(encoding="utf-8"))

    return load
