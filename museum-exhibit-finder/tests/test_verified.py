import copy

from mef.models import MuseumFile
from mef.verified import verified_offers_markdown

from conftest import TODAY


def _renovation_only(raw: dict) -> MuseumFile:
    raw = copy.deepcopy(raw)
    raw["museum"].update(id="renovating-museum", name="Renovating Museum")
    raw["contacts"] = []
    raw["exhibitions"] = [{"id": "hall", "name": "Old Hall", "status": "already_replaced", "evidence": ["e1"]}]
    raw["evidence"] = [raw["evidence"][0]]
    raw["research"].pop("outreach")
    return MuseumFile.model_validate(raw)


def _expired_offer(raw: dict) -> MuseumFile:
    raw = copy.deepcopy(raw)
    raw["museum"].update(id="closed-offer-museum", name="Closed Offer Museum")
    raw["evidence"][1]["valid_until"] = "2026-06-01"
    return MuseumFile.model_validate(raw)


def _section(text: str, start: str, end: str) -> str:
    return text.split(start, 1)[1].split(end, 1)[0]


def test_only_documented_current_offers_are_verified(sample, sample_raw):
    text = verified_offers_markdown([sample, _renovation_only(sample_raw), _expired_offer(sample_raw)], TODAY)
    verified = _section(text, "## Подтверждено", "## Предлагали")
    assert "Подтверждено: 1 организаций" in text
    assert "Example Science Centre" in verified
    assert "Van de Graaff generator" in verified
    assert "https://www.example-science.test/surplus" in verified      # offer proof
    assert "https://www.example-science.test/news/forces-lab" in verified  # removal proof
    assert "Bicycle generator" not in verified  # already given to someone else
    assert "Foucault pendulum" not in verified  # in storage, fate unknown
    assert "Renovating Museum" not in text      # renovation alone is not an offer


def test_expired_offer_moves_to_closed_table(sample_raw):
    text = verified_offers_markdown([_expired_offer(sample_raw)], TODAY)
    assert "Подтверждено: 0 организаций" in text
    closed = _section(text, "## Предлагали", "## Проверено и исключено")
    assert "Closed Offer Museum" in closed
    assert "2026-06-01" in closed


def test_excluded_channels_listed(sample):
    text = verified_offers_markdown([sample], TODAY)
    assert "## Проверено и исключено" in text
    assert "Heureka" in text.split("## Проверено и исключено", 1)[1]
