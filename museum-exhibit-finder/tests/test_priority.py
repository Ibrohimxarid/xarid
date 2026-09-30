import copy

from mef import POTENTIAL_LEAD
from mef.models import MuseumFile
from mef.priority import assess_exhibit, assess_museum, research_answers

from conftest import TODAY


def _items(mf):
    return {i.id: i for i in mf.exhibitions[0].exhibits}


def test_available_exhibit_is_A(sample):
    a = assess_exhibit(sample, _items(sample)["vdg"], TODAY)
    assert a.priority == "A"
    assert [e.id for e in a.availability_evidence] == ["e2"]


def test_stored_exhibit_is_B_potential_lead(sample):
    a = assess_exhibit(sample, _items(sample)["pendulum"], TODAY)
    assert a.priority == "B"
    assert a.availability == POTENTIAL_LEAD


def test_transferred_exhibit_is_not_an_opportunity(sample):
    a = assess_exhibit(sample, _items(sample)["bikes"], TODAY)
    assert a.priority is None


def test_museum_takes_best_priority(sample):
    assert assess_museum(sample, TODAY).priority == "A"


def test_stale_availability_downgraded_to_B(sample_raw):
    raw = copy.deepcopy(sample_raw)
    raw["evidence"][1]["source_date"] = "2019-01-01"
    mf = MuseumFile.model_validate(raw)
    a = assess_exhibit(mf, _items(mf)["vdg"], TODAY)
    assert a.priority == "B"
    assert "re-confirm" in " ".join(a.notes)


def test_renovation_only_is_C(sample_raw):
    raw = copy.deepcopy(sample_raw)
    raw["exhibitions"] = []
    raw["contacts"] = []
    raw["evidence"] = [dict(raw["evidence"][0], signals=["renovation", "new_exhibition"])]
    mf = MuseumFile.model_validate(raw)
    assert assess_museum(mf, TODAY).priority == "C"


def test_research_answers_cite_evidence(sample):
    ans = research_answers(sample, TODAY)
    assert len(ans) == 8
    assert "[e2]" in ans["5. Is the exhibit potentially available?"]
    assert ans["8. What is the original source?"].startswith("https://")
