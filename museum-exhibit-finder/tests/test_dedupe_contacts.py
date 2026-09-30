from mef.contacts import extract_contacts
from mef.dedupe import canonical_url, find_duplicate_museums, name_similarity, registered_domain


def test_canonical_url_strips_tracking_and_www():
    a = canonical_url("http://www.museum.org/news/?utm_source=x&id=3#top")
    b = canonical_url("https://museum.org/news?id=3")
    assert a == b


def test_registered_domain():
    assert registered_domain("https://www.sciencemuseum.org.uk/about") == "sciencemuseum.org.uk"


def test_duplicate_museums_by_name_and_domain():
    museums = [
        {"id": "a", "name": "Science Museum", "aliases": ["Science Museum London"], "country": "United Kingdom",
         "website": "https://www.sciencemuseum.org.uk"},
        {"id": "b", "name": "The Science Museum, London", "aliases": [], "country": "United Kingdom",
         "website": "https://sciencemuseum.org.uk/"},
        {"id": "c", "name": "Glasgow Science Centre", "aliases": [], "country": "United Kingdom",
         "website": "https://www.glasgowsciencecentre.org"},
    ]
    pairs = find_duplicate_museums(museums)
    assert {(p.a, p.b) for p in pairs} == {("a", "b")}


def test_name_similarity_ignores_stopwords():
    assert name_similarity("Deutsches Museum", "Deutsches Museum München") > 90


def test_extract_contacts_keeps_source_and_deobfuscates():
    text = ("For enquiries contact our Collections Manager at collections [at] museum [dot] org "
            "or call +44 20 7946 0000. Registrar: reg@museum.org")
    found = extract_contacts(text, "https://museum.org/contact")
    emails = {c.email for c in found if c.email}
    assert emails == {"collections@museum.org", "reg@museum.org"}
    assert all(c.source == "https://museum.org/contact" for c in found)
    assert any(c.phone for c in found)
    assert any(c.role == "Collections Manager" for c in found if c.email == "collections@museum.org")
