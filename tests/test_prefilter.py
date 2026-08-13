from src.prefilter import calendar_prefilter, is_relevant, matched_keywords


def test_matches_gold_keyword():
    assert is_relevant("Gold prices rally on safe-haven demand")


def test_matches_short_token_with_word_boundary():
    assert is_relevant("Fed holds rates steady")
    assert "fed" in matched_keywords("Fed holds rates steady")


def test_short_token_does_not_false_positive():
    # "principal" contains "pci"-adjacent letters but must not match "cpi"/"fed" etc.
    assert not is_relevant("School principal announces new policy")


def test_cpi_word_boundary():
    assert is_relevant("US CPI comes in hot")
    assert not is_relevant("The recipe calls for a cup of flour")


def test_irrelevant_headline():
    assert not is_relevant("Local bakery wins regional pastry award")


def test_calendar_prefilter_requires_high_or_medium_impact():
    assert calendar_prefilter("High", "CPI m/m") is True
    assert calendar_prefilter("Medium", "GDP q/q") is True
    assert calendar_prefilter("Low", "CPI m/m") is False
    assert calendar_prefilter(None, "CPI m/m") is False


def test_calendar_prefilter_still_requires_keyword_match():
    assert calendar_prefilter("High", "Bank Holiday") is False
