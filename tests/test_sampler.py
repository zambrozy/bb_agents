"""Tests for the DealSampler and its models."""

import pytest

from consts import CARDS_PER_HAND, Seat, Strain, Vulnerability
from models.sampler.cards import Deal, Hand
from sampler import DealSampler


def test_sample_deal_is_complete_and_disjoint():
    """A sampled deal holds all 52 distinct cards, 13 per seat."""
    deal = DealSampler(seed=1).sample_deal()
    assert set(deal.hands) == set(Seat)
    all_cards = []
    for seat in Seat:
        hand = deal.hands[seat]
        assert len(hand.cards) == CARDS_PER_HAND
        all_cards.extend((c.suit, c.rank) for c in hand.cards)
    assert len(all_cards) == 52
    assert len(set(all_cards)) == 52


def test_sampling_is_reproducible_with_seed():
    """The same seed yields the same deal."""
    a = DealSampler(seed=42).sample_deal()
    b = DealSampler(seed=42).sample_deal()
    assert a.to_pbn() == b.to_pbn()


def test_to_pbn_round_trips_through_dds():
    """PBN export is accepted by the DDS solver."""
    import dds3

    deal = DealSampler(seed=7).sample_deal()
    result = dds3.solve_board_pbn(deal.to_pbn(), trump=4)
    assert "score" in result


def test_pbn_segments_have_thirteen_cards():
    """Each PBN hand segment lists exactly 13 ranks."""
    deal = DealSampler(seed=3).sample_deal()
    for seat in Seat:
        segment = deal.hands[seat].pbn_segment()
        ranks = segment.replace(".", "")
        assert len(ranks) == CARDS_PER_HAND


def test_analyze_returns_full_trick_table():
    """Analysis covers every strain and seat with valid counts."""
    sampler = DealSampler(seed=11)
    deal = sampler.sample_deal()
    analysis = sampler.analyze(deal)
    for strain in Strain:
        for seat in Seat:
            tricks = analysis.tricks_for(strain, seat)
            assert 0 <= tricks <= 13
    assert analysis.par_score
    assert analysis.par_contracts


def test_sample_and_analyze_pairs_deal_with_analysis():
    """The convenience method returns a deal and its analysis."""
    deal, analysis = DealSampler(seed=99).sample_and_analyze(
        Vulnerability.NS
    )
    assert isinstance(deal, Deal)
    assert analysis.tricks_for(Strain.NOTRUMP, Seat.NORTH) >= 0


def test_format_deal_has_one_line_per_seat():
    """The readable deal layout prints one line per seat."""
    deal = DealSampler(seed=5).sample_deal()
    lines = deal.format().splitlines()
    assert len(lines) == 4
    assert lines[0].startswith("N")


def test_format_report_contains_key_sections():
    """The report bundles PBN, hand layout, and par info."""
    sampler = DealSampler(seed=2026)
    deal, analysis = sampler.sample_and_analyze()
    report = sampler.format_report(deal, analysis)
    assert deal.to_pbn() in report
    assert "Par score:" in report
    assert "Par contract:" in report
    assert "NT" in report


def test_hand_round_trips_through_both_notations():
    """Hand.from_str parses both to_str and pbn_segment output."""
    deal = DealSampler(seed=8).sample_deal()
    for hand in deal.hands.values():
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
    deal = DealSampler(seed=13).sample_deal()
    data = deal.to_dict()
    assert set(data) == {"N", "E", "S", "W"}
    assert Deal.from_dict(data).to_pbn() == deal.to_pbn()


def test_deal_from_dict_rejects_missing_seat_and_shared_card():
    """A missing seat or a card in two hands is rejected."""
    data = DealSampler(seed=13).sample_deal().to_dict()
    with pytest.raises(ValueError):
        Deal.from_dict({k: v for k, v in data.items() if k != "W"})
    with pytest.raises(ValueError):
        Deal.from_dict({**data, "W": data["N"]})
