"""Tests for the card models: Card, Hand, Deal, Deck."""

import random

import pytest

from consts import CARDS_PER_HAND, Seat
from models.cards import STANDARD_DECK, Deal, Hand


def _deal(seed: int) -> Deal:
    """A reproducible random deal (seed: int) -> Deal."""
    return STANDARD_DECK.deal(random.Random(seed))


def test_pbn_segments_have_thirteen_cards():
    """Each PBN hand segment lists exactly 13 ranks."""
    deal = _deal(3)
    for seat in Seat:
        segment = deal.hands[seat].pbn_segment()
        ranks = segment.replace(".", "")
        assert len(ranks) == CARDS_PER_HAND


def test_format_deal_has_one_line_per_seat():
    """The readable deal layout prints one line per seat."""
    lines = _deal(5).format().splitlines()
    assert len(lines) == 4
    assert lines[0].startswith("N")


def test_hand_round_trips_through_both_notations():
    """Hand.from_str parses both to_str and pbn_segment output."""
    for hand in _deal(8).hands.values():
        cards = set(hand.cards)
        assert set(Hand.from_str(hand.to_str()).cards) == cards
        assert set(Hand.from_str(hand.pbn_segment()).cards) == cards


def test_hand_from_str_handles_voids():
    """A void is '-' in readable form and empty in PBN."""
    text = "♠ AKQJT98765  ♥ -  ♦ 432  ♣ -"
    hand = Hand.from_str(text)
    assert hand.pbn_segment() == "AKQJT98765..432."
    assert hand.to_str() == text
    assert Hand.from_str("AKQJT98765..432.") == hand


@pytest.mark.parametrize(
    "text",
    [
        "AKQ.T98.J2",                      # three suits only
        "AKQ.T98.J2.543",                  # 12 cards
        "AKQ.T98.J2.5432X",                # bad rank char
        "AKQ ♥ T98  ♦ J2  ♣ 5432",         # rank before a symbol
        "♠ AKK  ♥ T98  ♦ J2  ♣ 5432",      # duplicate card
    ],
)
def test_hand_from_str_rejects_bad_input(text):
    """Malformed hand text raises ValueError."""
    with pytest.raises(ValueError):
        Hand.from_str(text)


def test_deal_round_trips_through_dict():
    """Deal.from_dict inverts Deal.to_dict."""
    deal = _deal(13)
    data = deal.to_dict()
    assert set(data) == {"N", "E", "S", "W"}
    assert Deal.from_dict(data).to_pbn() == deal.to_pbn()


def test_deal_from_dict_rejects_missing_seat_and_shared_card():
    """A missing seat or a card in two hands is rejected."""
    data = _deal(13).to_dict()
    with pytest.raises(ValueError):
        Deal.from_dict({k: v for k, v in data.items() if k != "W"})
    with pytest.raises(ValueError):
        Deal.from_dict({**data, "W": data["N"]})
