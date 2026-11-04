"""Tests for the DealSampler and its double-dummy analysis."""

from consts import CARDS_PER_HAND, Seat, Strain, Vulnerability
from models.cards import Deal
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


def test_format_report_contains_key_sections():
    """The report bundles PBN, hand layout, and par info."""
    sampler = DealSampler(seed=2026)
    deal, analysis = sampler.sample_and_analyze()
    report = sampler.format_report(deal, analysis)
    assert deal.to_pbn() in report
    assert "Par score:" in report
    assert "Par contract:" in report
    assert "NT" in report
