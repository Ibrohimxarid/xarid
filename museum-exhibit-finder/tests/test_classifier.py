from mef.classifier import classify, match_signals


def test_availability_text_is_A_candidate():
    text = ("The Science Discovery Centre closed its Physics Gallery in 2024. The old exhibits, "
            "including a Van de Graaff generator, are available to other museums. "
            "Interested institutions should contact the collections team.")
    c = classify("https://museum.test/news", text)
    assert c.is_museum
    assert c.priority == "A?"
    assert "available_transfer" in c.signals
    assert "electricity" in c.categories


def test_renovation_only_is_C_candidate():
    text = "The museum will open a brand new gallery after a major refurbishment in 2025."
    c = classify("https://museum.test/", text)
    assert c.priority == "C?"
    assert c.stage == 2


def test_removed_exhibits_is_B_candidate():
    text = "The science centre's old exhibits were dismantled and moved into storage."
    c = classify("https://sc.test/", text)
    assert c.priority == "B?"
    assert c.stage == 4


def test_commercial_supplier_excluded():
    text = "Our company designs and builds bespoke interactive exhibits. Request a quote today."
    c = classify("https://vendor.test/", text)
    assert c.commercial
    assert c.priority is None


def test_multilingual_signals():
    assert "deaccession_in_progress" in match_signals("Het museum gaat de collectie afstoten.")
    assert "for_sale" in match_signals("Die alten Exponate sind zu verkaufen.")
    assert "renovation" in match_signals("科学館のリニューアル")
    assert "new_exhibition" in match_signals("Nowa wystawa stała w centrum nauki")


def test_no_false_positive_on_plain_text():
    c = classify("https://blog.test/", "I had a lovely lunch in the park yesterday.")
    assert c.priority is None
    assert c.signals == {}
