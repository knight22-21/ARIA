"""Tests for B2B receivables pure logic + Hinglish guidance."""

import pytest

from app.agents.hinglish import build_message_guidance
from app.detection.aging import aging_bucket
from app.ingestion.invoices import _to_paise


def test_aging_buckets():
    assert aging_bucket(-5) == "current"
    assert aging_bucket(0) == "current"
    assert aging_bucket(15) == "0-30"
    assert aging_bucket(30) == "0-30"
    assert aging_bucket(45) == "31-60"
    assert aging_bucket(75) == "61-90"
    assert aging_bucket(120) == "90+"


def test_to_paise():
    assert _to_paise("40000") == 4_000_000
    assert _to_paise("1,25,000") == 12_500_000  # Indian grouping tolerated
    assert _to_paise("199.50") == 19_950
    with pytest.raises(ValueError):
        _to_paise("not-a-number")


def test_hinglish_guidance_switches_language():
    english = build_message_guidance("english")
    hinglish = build_message_guidance("hinglish", "enterprise")
    assert "English" in english
    assert "Hinglish" in hinglish
    # Enterprise tone note should be referenced for enterprise tier.
    assert "aap" in hinglish.lower() or "formal" in hinglish.lower()
