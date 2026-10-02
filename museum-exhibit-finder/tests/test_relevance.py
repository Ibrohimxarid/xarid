import copy
from mef.candidates import build
from mef.candidates_out import candidates_markdown
from mef.models import MuseumFile, Relevance
from mef.relevance import classify, why_it_fits_problems

from conftest import TODAY


def test_classify_rules():
    assert classify(["physics"], "interactive_station")[0] == Relevance.DIRECT_MATCH
    assert classify(["automotive"], "cutaway")[0] == Relevance.DIRECT_MATCH
    assert classify(["aviation"], "engine")[0] == Relevance.DIRECT_MATCH
    assert classify(["automotive"], "vehicle")[0] == Relevance.STRONG_MATCH
    assert classify(["computing"], "computer")[0] == Relevance.STRONG_MATCH
    assert classify(["industrial"], "component")[0] == Relevance.RELATED
    assert classify(["thermodynamics"], "household")[0] == Relevance.WEAK_MATCH
    assert classify(["engineering"], "book_document")[0] == Relevance.NOT_RELEVANT
    assert classify(["display_cases"], "display_furniture")[0] == Relevance.NOT_RELEVANT
    assert classify(["art"], "model")[0] == Relevance.NOT_RELEVANT
    assert classify(["automotive"], "mixed_collection")[0] is None  # a channel, not a candidate


def test_why_it_fits_rejects_generic_text():
    assert why_it_fits_problems(None) == ["отсутствует"]
    assert why_it_fits_problems("Interesting for the museum.")
    ok = ("Interactive engine cutaway demonstrates piston movement, combustion and power transmission. "
          "Fits the museum's automotive technology and interactive engineering areas.")
    assert why_it_fits_problems(ok) == []


def test_acquisition_priority(sample):
    cands, chans, rejected = build([sample], TODAY)
    by = {c.label: c for c in cands}
    vdg = by["Van de Graaff generator"].acquisition
    assert vdg.relevance == Relevance.DIRECT_MATCH and vdg.priority == "HIGH"
    pend = by["Foucault pendulum"].acquisition
    assert pend.priority == "LOW"  # condition, logistics and availability are all open
    assert "Bicycle generator" not in by  # already given to someone else


def test_one_open_check_gives_medium(sample_raw):
    raw = copy.deepcopy(sample_raw)
    raw["research"]["international_transfer"] = "domestic_first"
    mf = MuseumFile.model_validate(raw)
    vdg = next(c for c in build([mf], TODAY)[0] if c.label == "Van de Graaff generator").acquisition
    assert vdg.priority == "MEDIUM"
    assert [c.name for c in vdg.open_checks] == ["Разумная логистика"]


def test_books_are_not_recommended(sample_raw):
    raw = copy.deepcopy(sample_raw)
    item = raw["exhibitions"][0]["exhibits"][0]
    item.update(name="41 volumes of engineering proceedings", object_type="book_document")
    mf = MuseumFile.model_validate(raw)
    cands, _, rejected = build([mf], TODAY)
    assert "41 volumes of engineering proceedings" not in {c.label for c in cands}
    assert [c.label for c in rejected] == ["41 volumes of engineering proceedings"]
    text = candidates_markdown([mf], TODAY)
    assert "41 volumes of engineering proceedings" in text.split("## Не рекомендовать", 1)[1]


def test_expired_offer_is_not_high(sample_raw):
    raw = copy.deepcopy(sample_raw)
    raw["evidence"][1]["valid_until"] = "2026-06-01"
    mf = MuseumFile.model_validate(raw)
    vdg = next(c for c in build([mf], TODAY)[0] if c.label == "Van de Graaff generator").acquisition
    assert vdg.priority == "MEDIUM"
    assert vdg.open_checks[0].name == "Доступность подтверждена сейчас"
