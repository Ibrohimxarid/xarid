import copy

import pytest
from pydantic import ValidationError

from mef.models import MuseumFile


def test_sample_is_valid(sample):
    assert sample.museum.id == "example-science-centre"
    assert len(sample.exhibitions[0].exhibits) == 3


def test_unknown_evidence_reference_rejected(sample_raw):
    raw = copy.deepcopy(sample_raw)
    raw["exhibitions"][0]["exhibits"][0]["evidence"] = ["e99"]
    with pytest.raises(ValidationError, match="unknown evidence id"):
        MuseumFile.model_validate(raw)


def test_status_without_evidence_rejected(sample_raw):
    raw = copy.deepcopy(sample_raw)
    raw["exhibitions"][0]["exhibits"][0]["evidence"] = []
    with pytest.raises(ValidationError, match="needs evidence"):
        MuseumFile.model_validate(raw)


def test_typo_field_rejected(sample_raw):
    raw = copy.deepcopy(sample_raw)
    raw["museum"]["wesbite"] = "https://typo.test"
    with pytest.raises(ValidationError):
        MuseumFile.model_validate(raw)


def test_bad_date_rejected(sample_raw):
    raw = copy.deepcopy(sample_raw)
    raw["evidence"][0]["source_date"] = "March 2024"
    with pytest.raises(ValidationError, match="YYYY"):
        MuseumFile.model_validate(raw)


def test_museum_needs_evidence(sample_raw):
    raw = copy.deepcopy(sample_raw)
    raw["evidence"] = []
    raw["exhibitions"] = []
    raw["contacts"] = []
    with pytest.raises(ValidationError, match="at least one evidence"):
        MuseumFile.model_validate(raw)
