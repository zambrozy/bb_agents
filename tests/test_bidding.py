"""Tests for Call and BiddingHistory."""

import pytest

from consts import CallType, Seat, Strain
from models.bidding import BiddingHistory, Call


def _play(dealer: Seat, calls: list[Call]) -> BiddingHistory:
    """Build a history by adding `calls` in order."""
    history = BiddingHistory(dealer=dealer)
    for call in calls:
        history.add(call)
    return history


def test_call_validation_and_text():
    """Only bids carry level and strain; str is compact."""
    assert str(Call.bid(1, Strain.NOTRUMP)) == "1NT"
    assert str(Call.make_pass()) == "P"
    assert str(Call.double()) == "X"
    assert str(Call.redouble()) == "XX"
    with pytest.raises(ValueError):
        Call(kind=CallType.BID, level=1)
    with pytest.raises(ValueError):
        Call(kind=CallType.PASS, level=1, strain=Strain.CLUBS)
    with pytest.raises(ValueError):
        Call.bid(8, Strain.CLUBS)


def test_bid_ranking():
    """Higher level or higher strain outranks."""
    spades = Call.bid(1, Strain.SPADES)
    assert spades.rank > Call.bid(1, Strain.HEARTS).rank
    assert Call.bid(2, Strain.CLUBS).rank > Call.bid(1, Strain.NOTRUMP).rank


def test_add_mutates_and_rotates_seats():
    """`add` appends in place and moves to the next seat."""
    history = BiddingHistory(dealer=Seat.WEST)
    assert history.next_seat == Seat.WEST
    history.add(Call.bid(1, Strain.CLUBS))
    assert len(history.calls) == 1
    assert history.next_seat == Seat.NORTH


def test_insufficient_bid_is_rejected():
    """A bid must outrank the previous one."""
    history = _play(Seat.NORTH, [Call.bid(1, Strain.SPADES)])
    with pytest.raises(ValueError):
        history.add(Call.bid(1, Strain.HEARTS))
    history.add(Call.bid(1, Strain.NOTRUMP))


def test_double_and_redouble_rules():
    """Double needs an opposing bid; redouble an opposing double."""
    history = BiddingHistory(dealer=Seat.NORTH)
    assert not history.is_legal(Call.double())
    history.add(Call.bid(1, Strain.CLUBS))  # N
    assert history.is_legal(Call.double())  # E
    history.add(Call.make_pass())  # E
    assert not history.is_legal(Call.double())  # S: partner's bid
    history.add(Call.make_pass())  # S
    assert history.is_legal(Call.double())  # W
    history.add(Call.double())  # W
    assert history.is_legal(Call.redouble())  # N
    assert not history.is_legal(Call.double())
    history.add(Call.redouble())
    assert not history.is_legal(Call.redouble())


def test_passed_out_auction():
    """Four passes end an auction with no contract."""
    history = _play(Seat.SOUTH, [Call.make_pass()] * 4)
    assert history.is_over
    assert history.contract is None
    assert history.legal_calls() == []
    with pytest.raises(ValueError):
        history.add(Call.make_pass())


def test_three_passes_end_after_bid():
    """Three passes after a bid end the auction."""
    history = _play(
        Seat.NORTH, [Call.bid(1, Strain.HEARTS)] + [Call.make_pass()] * 2
    )
    assert not history.is_over
    history.add(Call.make_pass())
    assert history.is_over


def test_contract_declarer_is_first_to_bid_strain():
    """Declarer is the partner who first named the final strain."""
    history = _play(
        Seat.NORTH,
        [
            Call.bid(1, Strain.HEARTS),  # N
            Call.make_pass(),  # E
            Call.bid(2, Strain.HEARTS),  # S
            Call.make_pass(),  # W
            Call.bid(4, Strain.HEARTS),  # N
            Call.double(),  # E
            Call.make_pass(),
            Call.make_pass(),
            Call.make_pass(),
        ],
    )
    contract = history.contract
    assert contract.declarer == Seat.NORTH
    assert (contract.level, contract.strain) == (4, Strain.HEARTS)
    assert contract.doubled and not contract.redoubled
    assert str(contract) == "4H X by NORTH"


def test_declarer_when_partner_bid_strain_first():
    """South opened the suit first, so South declares even if N raised."""
    history = _play(
        Seat.SOUTH,
        [
            Call.bid(1, Strain.SPADES),  # S
            Call.make_pass(),  # W
            Call.bid(4, Strain.SPADES),  # N
            Call.make_pass(),
            Call.make_pass(),
            Call.make_pass(),
        ],
    )
    assert history.contract.declarer == Seat.SOUTH


def test_legal_calls_start_of_auction():
    """At the start: pass and all 35 bids, no double or redouble."""
    calls = BiddingHistory(dealer=Seat.EAST).legal_calls()
    assert len(calls) == 36
    assert Call.double() not in calls


def test_legal_calls_after_seven_notrump():
    """After 7NT only pass and double remain."""
    history = _play(Seat.NORTH, [Call.bid(7, Strain.NOTRUMP)])
    assert set(history.legal_calls()) == {Call.make_pass(), Call.double()}
