"""Pydantic models of the deal endpoints of the web service."""

from typing import Self

from pydantic import BaseModel

from consts import (
    SEAT_NAMES,
    SEAT_TO_PBN,
    STRAIN_TO_CHAR,
    VULNERABILITY_NAMES,
    Seat,
    Suit,
    Vulnerability,
)
from models.cards import Deal, Hand
from models.sampler import DealAnalysis


class DealRequest(BaseModel):
    """Parameters of a new deal.

    Attributes:
        seed (int | None): Seed for a reproducible deal; random if
            None.
        dealer (SEAT_NAMES): Seat that calls first.
        vulnerability (VULNERABILITY_NAMES): Vulnerable side(s).
    """

    seed: int | None = None
    dealer: SEAT_NAMES = "NORTH"
    vulnerability: VULNERABILITY_NAMES = "NONE"


class HandView(BaseModel):
    """One hand as shown in the UI.

    Attributes:
        suits (list[str]): Ranks per suit in S, H, D, C order,
            highest first, e.g. 'AKT'; '' for a void.
        hcp (int): High card points.
    """

    suits: list[str]
    hcp: int

    @classmethod
    def from_hand(cls, hand: Hand) -> Self:
        """Build the view of a hand (Hand) -> HandView."""
        return cls(
            suits=[hand.suit_chars(suit) for suit in Suit],
            hcp=hand.hcp,
        )


class AnalysisView(BaseModel):
    """Double-dummy analysis as shown in the UI.

    Attributes:
        tricks (dict[str, dict[str, int]]): Strain label ('NT', 'S',
            ...) -> seat letter ('N', ...) -> tricks for that
            declarer.
        par_score (list[str]): Par scores per side.
        par_contracts (list[str]): Par contract(s) in DDS notation.
    """

    tricks: dict[str, dict[str, int]]
    par_score: list[str]
    par_contracts: list[str]

    @classmethod
    def from_analysis(cls, analysis: DealAnalysis) -> Self:
        """Build the view of an analysis (DealAnalysis)
        -> AnalysisView."""
        return cls(
            tricks={
                STRAIN_TO_CHAR[strain]: {
                    SEAT_TO_PBN[seat]: tricks
                    for seat, tricks in row.items()
                }
                for strain, row in analysis.tricks.items()
            },
            par_score=analysis.par_score,
            par_contracts=analysis.par_contracts,
        )


class DealView(BaseModel):
    """A deal with its analysis, as returned by the API.

    Attributes:
        id (str): Deal id used by the bidding endpoint.
        dealer (SEAT_NAMES): Seat that calls first.
        vulnerability (VULNERABILITY_NAMES): Vulnerable side(s).
        pbn (str): The deal in PBN.
        hands (dict[SEAT_NAMES, HandView]): Hand per seat.
        analysis (AnalysisView): Double-dummy tricks and par.
    """

    id: str
    dealer: SEAT_NAMES
    vulnerability: VULNERABILITY_NAMES
    pbn: str
    hands: dict[SEAT_NAMES, HandView]
    analysis: AnalysisView


class DealRecord(BaseModel):
    """A deal kept by the service between requests.

    Attributes:
        id (str): Deal id.
        deal (Deal): The four hands.
        analysis (DealAnalysis): Its double-dummy analysis.
        dealer (Seat): Seat that calls first.
        vulnerability (Vulnerability): Vulnerable side(s).
    """

    id: str
    deal: Deal
    analysis: DealAnalysis
    dealer: Seat
    vulnerability: Vulnerability

    def to_view(self) -> DealView:
        """Render the record for the API (-> DealView)."""
        return DealView(
            id=self.id,
            dealer=self.dealer.name,
            vulnerability=self.vulnerability.name,
            pbn=self.deal.to_pbn(),
            hands={
                seat.name: HandView.from_hand(self.deal.hands[seat])
                for seat in Seat
            },
            analysis=AnalysisView.from_analysis(self.analysis),
        )
