"""Pydantic models for double-dummy deal analysis results."""

from pydantic import BaseModel

from consts import Seat, Strain


class DealAnalysis(BaseModel):
    """Double-dummy analysis of a single deal.

    Attributes:
        tricks (dict[Strain, dict[Seat, int]]): Tricks the declarer
            at each seat can take in each strain (double dummy).
        par_score (list[str]): Par scores per side, e.g.
            ['NS 1510', 'EW -1510'].
        par_contracts (list[str]): Par contract(s) in DDS notation.
    """

    tricks: dict[Strain, dict[Seat, int]]
    par_score: list[str]
    par_contracts: list[str]

    def tricks_for(self, strain: Strain, declarer: Seat) -> int:
        """Tricks available for `declarer` in `strain` (int)."""
        return self.tricks[strain][declarer]
