import datetime as dt
from pathlib import Path

import pytest
import yaml

from mef.models import MuseumFile

FIXTURES = Path(__file__).parent / "fixtures"
TODAY = dt.date(2026, 9, 30)


@pytest.fixture
def sample_raw() -> dict:
    return yaml.safe_load((FIXTURES / "sample_museum.yaml").read_text(encoding="utf-8"))


@pytest.fixture
def sample(sample_raw) -> MuseumFile:
    return MuseumFile.model_validate(sample_raw)
