"""Tests for Call and BiddingHistory."""

import pytest

from consts.bidding import CHAR_TO_STRAIN, CallType, Strain
from consts.cards import Seat, Vulnerability
from models.bidding import (
    BiddingHistory,
    Call,
    Contract,
    ContractResult,
    PlayerReply,
)
from models.sampler import DealAnalysis


def _play(dealer: Seat, calls: list[Call]) -> BiddingHistory:
    """Build a history by adding `calls` in order."""
    history = BiddingHistory(dealer=dealer, vulnerability=Vulnerability.NONE)
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
    history = BiddingHistory(
        dealer=Seat.WEST, vulnerability=Vulnerability.NONE
    )
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
    history = BiddingHistory(
        dealer=Seat.NORTH, vulnerability=Vulnerability.NONE
    )
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
    history = BiddingHistory(
        dealer=Seat.EAST, vulnerability=Vulnerability.NONE
    )
    calls = history.legal_calls()
    assert len(calls) == 36
    assert Call.double() not in calls


def _all_calls() -> list[Call]:
    """Every possible call: pass, double, redouble and 35 bids."""
    bids = [
        Call.bid(level, strain)
        for level in range(1, 8)
        for strain in Strain
    ]
    return [Call.make_pass(), Call.double(), Call.redouble(), *bids]


def test_from_str_round_trips_every_call():
    """`from_str(str(call))` gives back the same call."""
    calls = _all_calls()
    assert len(calls) == 38
    for call in calls:
        assert Call.from_str(str(call)) == call


def test_from_str_ignores_case_and_spaces():
    """Whitespace and letter case do not matter."""
    assert Call.from_str(" 3nt ") == Call.bid(3, Strain.NOTRUMP)
    assert Call.from_str("p") == Call.make_pass()
    assert Call.from_str("xx") == Call.redouble()


@pytest.mark.parametrize(
    "text", ["", "8C", "0S", "1X", "1", "NT", "BID", "pass", "1NTT"]
)
def test_from_str_rejects_invalid_text(text):
    """Strings that are not calls raise ValueError."""
    with pytest.raises(ValueError):
        Call.from_str(text)


def test_player_reply_converts_to_call():
    """A valid reply converts to a Call; a bad one fails on build."""
    reply = PlayerReply(reasoning="12 HCP, balanced", call="1NT")
    assert reply.to_call() == Call.bid(1, Strain.NOTRUMP)
    with pytest.raises(ValueError):
        PlayerReply(reasoning="oops", call="8C")


def _table_cells(history: BiddingHistory) -> list[list[str]]:
    """Table rows split into cells, ignoring column padding."""
    return [line.split() for line in history.to_table().splitlines()]


def test_to_table_pads_rows_before_the_dealer():
    """South dealing: the first row starts with two `-` cells."""
    history = _play(
        Seat.SOUTH,
        [
            Call.bid(1, Strain.HEARTS), Call.make_pass(),
            Call.bid(2, Strain.HEARTS), Call.make_pass(),
            Call.bid(4, Strain.HEARTS), Call.make_pass(),
            Call.make_pass(), Call.make_pass(),
        ],
    )
    assert _table_cells(history) == [
        ["N", "E", "S", "W"],
        ["-", "-", "1H", "P"],
        ["2H", "P", "4H", "P"],
        ["P", "P"],
    ]


def test_to_table_with_no_calls_yet():
    """An empty auction shows the header, plus padding if needed."""
    north = _play(Seat.NORTH, [])
    west = _play(Seat.WEST, [])
    assert _table_cells(north) == [["N", "E", "S", "W"]]
    assert _table_cells(west) == [["N", "E", "S", "W"], ["-", "-", "-"]]


def test_to_list_names_the_seat_of_each_call():
    """Calls are listed in order, starting from the dealer."""
    history = _play(
        Seat.EAST,
        [Call.bid(1, Strain.SPADES), Call.double(), Call.make_pass()],
    )
    assert history.to_list() == ["EAST: 1S", "SOUTH: X", "WEST: P"]
    assert _play(Seat.NORTH, []).to_list() == []


def test_legal_calls_after_seven_notrump():
    """After 7NT only pass and double remain."""
    history = _play(Seat.NORTH, [Call.bid(7, Strain.NOTRUMP)])
    assert set(history.legal_calls()) == {Call.make_pass(), Call.double()}


def _contract(text: str) -> Contract:
    """Contract by NORTH from text like '4H', '3NTX', '1SXX'
    (str) -> Contract."""
    bid = text.rstrip("X")
    marks = len(text) - len(bid)
    return Contract(
        level=int(bid[0]),
        strain=CHAR_TO_STRAIN[bid[1:]],
        declarer=Seat.NORTH,
        doubled=marks == 1,
        redoubled=marks == 2,
    )


@pytest.mark.parametrize(("text", "tricks", "vul", "score"), [
    # Part scores and games, undoubled.
    ("2C", 8, False, 90),
    ("1NT", 8, False, 120),
    ("3NT", 9, False, 400),
    ("3NT", 10, True, 630),
    ("4H", 10, False, 420),
    ("4S", 11, True, 650),
    ("5D", 11, False, 400),
    # Slams.
    ("6S", 12, False, 980),
    ("6NT", 12, True, 1440),
    ("7NT", 13, True, 2220),
    ("7C", 13, False, 1440),
    # Doubled and redoubled makes: game by doubling, insult,
    # overtricks.
    ("1NTX", 7, False, 180),
    ("2HX", 8, False, 470),
    ("2HX", 9, True, 870),
    ("1SXX", 7, False, 520),
    ("1NTXX", 7, False, 560),
    ("1NTXX", 8, True, 1160),
    ("4SXX", 11, False, 1080),
    # Undertricks.
    ("4H", 8, False, -100),
    ("4H", 7, True, -300),
    ("3SX", 8, False, -100),
    ("3SX", 6, False, -500),
    ("3SX", 5, False, -800),
    ("3SX", 4, False, -1100),
    ("3SX", 7, True, -500),
    ("3SX", 5, True, -1100),
    ("3SXX", 8, False, -200),
    ("3SXX", 5, False, -1600),
    ("3SXX", 7, True, -1000),
    ("3SXX", 6, True, -1600),
])
def test_contract_score(text, tricks, vul, score):
    """Duplicate score of the declarer's side."""
    assert _contract(text).score(tricks, vul) == score


def test_vulnerability_of_seat():
    """Each vulnerability covers the right sides."""
    assert not Vulnerability.NONE.is_vulnerable(Seat.NORTH)
    assert Vulnerability.BOTH.is_vulnerable(Seat.WEST)
    assert Vulnerability.NS.is_vulnerable(Seat.SOUTH)
    assert not Vulnerability.NS.is_vulnerable(Seat.EAST)
    assert Vulnerability.EW.is_vulnerable(Seat.EAST)
    assert not Vulnerability.EW.is_vulnerable(Seat.NORTH)


def _analysis(par_ns: int) -> DealAnalysis:
    """Analysis where every declarer takes 9 tricks, with the given
    par (int) -> DealAnalysis."""
    return DealAnalysis(
        tricks={s: {seat: 9 for seat in Seat} for s in Strain},
        par_score=[f"NS {par_ns}", f"EW {-par_ns}"],
        par_contracts=[],
    )


def test_contract_result_scores_from_ns_view():
    """An EW contract counts negative for NS; vs_par compares with
    the NS par."""
    history = BiddingHistory(
        dealer=Seat.EAST, vulnerability=Vulnerability.EW
    )
    for text in ["3NT", "P", "P", "P"]:
        history.add(Call.from_str(text))

    result = ContractResult.from_history(history, _analysis(-400))
    assert result.contract == "3NT by EAST"
    assert result.dd_tricks == 9 and result.result == 0
    assert result.score_ns == -600
    assert result.par_ns == -400
    assert result.vs_par == -200


def test_contract_result_passed_out():
    """A passed-out auction scores 0 against par."""
    history = _play(Seat.NORTH, [Call.make_pass()] * 4)
    result = ContractResult.from_history(history, _analysis(140))
    assert result.contract is None
    assert result.score_ns == 0
    assert result.vs_par == -140
