import os
import unittest

from exhibit_finder import database, queries
from exhibit_finder.models import Candidate
from exhibit_finder.relevance import (check, validate_why_it_fits, DIRECT_MATCH, STRONG_MATCH, RELATED,
                                      WEAK_MATCH, NOT_RELEVANT)
from exhibit_finder.priority import assess, HIGH, MEDIUM, LOW

EXAMPLES = os.path.join(os.path.dirname(__file__), "..", "data", "example_candidates.json")


def cand(title, **kw):
    return Candidate(id=kw.pop("id", title[:10]), title=title, **kw)


def ready(title, **kw):
    """A candidate that meets every acquisition criterion except relevance."""
    base = dict(source_type="science_centre", exhibit_status="FOR_TRANSFER", condition="working",
                evidence_url="https://example.org/offer", evidence_type="official_museum_document",
                logistics_reasonable=True, photos_available=True, contact_email="a@example.org",
                international_transfer="yes")
    base.update(kw)
    return cand(title, **base)


class RelevanceTest(unittest.TestCase):
    def rel(self, title, **kw):
        return check(cand(title, **kw)).relevance

    def test_group_a_is_direct_match(self):
        for title in ("Interactive Engine Cutaway", "Tesla coil", "Van de Graaff generator", "KUKA robotic arm",
                      "Wind tunnel", "Earthquake simulator table", "Railway signalling demonstrator",
                      "Gearbox cutaway", "Foucault pendulum", "Multi-touch table", "Robotic welding cell",
                      "Flight simulator", "Infinity mirror", "Bernoulli blower"):
            with self.subTest(title=title):
                self.assertEqual(self.rel(title), DIRECT_MATCH)

    def test_concept_from_description(self):
        self.assertEqual(self.rel("Exhibit 42", description="Hands-on Tesla coil station with safety cage"),
                         DIRECT_MATCH)

    def test_group_b_is_strong_match(self):
        self.assertEqual(self.rel("Manual telephone switchboard"), STRONG_MATCH)
        self.assertEqual(self.rel("Soviet mainframe computer"), STRONG_MATCH)

    def test_spec_bad_example_books(self):
        r = check(cand("41 volumes of books", object_type="books",
                       description="Bound volumes of a regional history series."))
        self.assertEqual(r.relevance, NOT_RELEVANT)

    def test_group_c_with_technology_connection_is_weak(self):
        self.assertEqual(self.rel("Photograph of a steam locomotive"), WEAK_MATCH)
        self.assertEqual(self.rel("Workshop manual", description="Service manual for a diesel engine"), WEAK_MATCH)

    def test_excluded_types_never_relevant(self):
        self.assertEqual(self.rel("Oil painting of a steam engine"), NOT_RELEVANT)
        self.assertEqual(self.rel("Bronze sculpture", description="Abstract robot figure"), NOT_RELEVANT)
        self.assertEqual(self.rel("Archaeological pottery shard"), NOT_RELEVANT)

    def test_object_type_overrides_title(self):
        self.assertEqual(self.rel("Wind tunnel", object_type="poster"), WEAK_MATCH)

    def test_first_decisive_term_wins(self):
        self.assertEqual(self.rel("Engine cutaway with information posters"), DIRECT_MATCH)

    def test_head_noun_decides_object_kind(self):
        self.assertEqual(self.rel("Collection of 300 railway timetables"), WEAK_MATCH)
        self.assertEqual(self.rel("Locomotive nameplate"), WEAK_MATCH)
        self.assertEqual(self.rel("Model of a steam engine"), DIRECT_MATCH)
        self.assertEqual(self.rel("Hall of Mirrors exhibit"), DIRECT_MATCH)
        self.assertEqual(self.rel("Rotating chair"), DIRECT_MATCH)
        self.assertEqual(self.rel("Lot 214: Victorian mahogany chair"), NOT_RELEVANT)
        self.assertEqual(self.rel("Manual telephone switchboard"), STRONG_MATCH)

    def test_consumer_products_not_matched(self):
        self.assertEqual(self.rel("Plasma screen TV"), NOT_RELEVANT)
        self.assertEqual(self.rel("Magnet fishing game"), NOT_RELEVANT)

    def test_toys_capped_at_weak(self):
        self.assertEqual(self.rel("Toy steam engine"), WEAK_MATCH)  # "toy" is also a Group C type
        self.assertEqual(self.rel("Die-cast souvenir locomotive", object_type="souvenir model"), WEAK_MATCH)

    def test_general_technology_is_related(self):
        self.assertEqual(self.rel("Scientific instrument, unidentified"), RELATED)

    def test_prose_does_not_trigger(self):
        r = check(cand("Wooden chest", description="A broad spectrum of uses; the gravity of the era; "
                                                    "funding mechanism; museum staff induction."))
        self.assertEqual(r.relevance, NOT_RELEVANT)

    def test_nothing_technological(self):
        self.assertEqual(self.rel("Embroidered wedding dress"), NOT_RELEVANT)

    def test_plural_and_hyphen_variants(self):
        self.assertEqual(self.rel("Two engine cut-aways"), DIRECT_MATCH)
        self.assertEqual(self.rel("Collaborative robots"), DIRECT_MATCH)


class PriorityTest(unittest.TestCase):
    def prio(self, c):
        return assess(c, check(c))

    def test_all_criteria_true_is_high(self):
        p = self.prio(ready("Interactive engine cutaway"))
        self.assertEqual(p.priority, HIGH)
        self.assertTrue(p.ideal_target)

    def test_one_uncertainty_is_medium(self):
        p = self.prio(ready("Tesla coil", logistics_reasonable=None))
        self.assertEqual(p.priority, MEDIUM)
        self.assertEqual(p.uncertain, ["reasonable logistics"])

    def test_two_uncertainties_is_low(self):
        p = self.prio(ready("Tesla coil", logistics_reasonable=None, condition="unknown"))
        self.assertEqual(p.priority, LOW)

    def test_availability_alone_is_not_enough(self):
        # Offered with evidence, but it is a book: availability must not lift it.
        p = self.prio(ready("Book on locomotives"))
        self.assertEqual(p.priority, LOW)

    def test_availability_claim_without_evidence_is_uncertain(self):
        p = self.prio(ready("Tesla coil", evidence_url=""))
        self.assertIsNone(p.criteria["availability_confirmed"])
        self.assertEqual(p.priority, MEDIUM)

    def test_sold_or_on_display_is_low(self):
        for status in ("SOLD", "ON_DISPLAY", "SCRAPPED"):
            with self.subTest(status=status):
                p = self.prio(ready("Tesla coil", exhibit_status=status))
                self.assertFalse(p.criteria["availability_confirmed"])
                self.assertEqual(p.priority, LOW)

    def test_unusable_is_low(self):
        self.assertEqual(self.prio(ready("Tesla coil", condition="unusable")).priority, LOW)

    def test_related_is_low_even_if_available(self):
        self.assertEqual(self.prio(ready("Scientific instrument, unidentified")).priority, LOW)

    def test_ideal_target_gaps(self):
        p = self.prio(ready("Tesla coil", international_transfer="unknown", contact_email=""))
        self.assertFalse(p.ideal_target)
        self.assertIn("no contact person", p.ideal_target_gaps)
        self.assertIn("international transfer not confirmed possible", p.ideal_target_gaps)


class WhyItFitsTest(unittest.TestCase):
    def test_generated_text_is_concrete(self):
        rec = database.evaluate(ready("Robotic arm programming station", description="Visitors program a robot arm"))
        why = rec["WHY_IT_FITS_TASHKENT_POLYTECHNIC_MUSEUM"]
        self.assertIn("robot", why.lower())
        self.assertIn("robotics", why)
        self.assertEqual(validate_why_it_fits(why, check(ready("Robotic arm programming station"))), [])

    def test_generic_text_rejected_and_replaced(self):
        rec = database.evaluate(ready("Tesla coil", why_it_fits="Interesting for the museum."))
        self.assertTrue(rec["why_it_fits_rejected"])
        self.assertIn("high-voltage", rec["WHY_IT_FITS_TASHKENT_POLYTECHNIC_MUSEUM"])

    def test_good_researcher_text_kept(self):
        text = ("Retired Tesla coil show demonstrates high-voltage resonance and electrical discharge. "
                "Fits the museum's electricity and interactive science areas.")
        rec = database.evaluate(ready("Tesla coil", why_it_fits=text))
        self.assertEqual(rec["WHY_IT_FITS_TASHKENT_POLYTECHNIC_MUSEUM"], text)


class DatabaseTest(unittest.TestCase):
    def test_spec_examples(self):
        db, rejected = database.build(database.load_candidates(EXAMPLES))
        self.assertEqual([r["id"] for r in db], ["EX-001"])
        self.assertEqual(db[0]["MUSEUM_RELEVANCE"], DIRECT_MATCH)
        self.assertEqual(db[0]["ACQUISITION_PRIORITY"], HIGH)
        self.assertEqual(rejected[0]["id"], "EX-002")
        self.assertEqual(rejected[0]["result"], "DO NOT RECOMMEND")

    def test_weak_excluded_by_default(self):
        cands = [cand("Photograph of a steam locomotive")]
        self.assertEqual(database.build(cands)[0], [])
        self.assertEqual(len(database.build(cands, include_weak=True)[0]), 1)

    def test_sorting_high_first(self):
        db, _ = database.build([ready("Tesla coil", id="b", logistics_reasonable=None),
                                ready("Engine cutaway", id="a")])
        self.assertEqual([r["id"] for r in db], ["a", "b"])

    def test_unknown_field_rejected(self):
        with self.assertRaises(ValueError):
            Candidate.from_dict({"id": "x", "title": "y", "colour": "red"})


class QueriesTest(unittest.TestCase):
    def test_queries_are_targeted(self):
        rows = list(queries.generate())
        self.assertTrue(rows)
        for r in rows:
            q = r["query"]
            self.assertTrue(any(p.split('"')[1] in q for p in queries.RETIREMENT_PHRASES), q)
            self.assertTrue(any(s in q for s in queries.SOURCE_PHRASES), q)
            self.assertIn("-book", q)


if __name__ == "__main__":
    unittest.main()
