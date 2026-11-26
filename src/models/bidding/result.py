"""Pydantic model of an auction's result against double dummy."""

from typing import Self

from pydantic import BaseModel

from consts.bidding import STRAIN_TO_CHAR
from consts.cards import SEAT_NAMES, Seat
from models.bidding.history import BiddingHistory
from models.sampler import DealAnalysis


class ContractResult(BaseModel):
    """Final contract played double dummy, scored and compared to par.

    Scores are from North-South's view (as DDS gives par): positive
    when NS gain points.

    Attributes:
        contract (str | None): e.g. '4H X by NORTH'; None if passed
            out.
        declarer (SEAT_NAMES | None): Declarer; None if passed out.
        strain (str | None): Contract strain label, e.g. 'H'.
        dd_tricks (int | None): Tricks the declarer takes double
            dummy.
        needed (int | None): Tricks the contract needs.
        result (int | None): dd_tricks - needed; >= 0 makes.
        score_ns (int): Score of the contract; 0 if passed out.
        par_ns (int): Par score of the deal.
        vs_par (int): score_ns - par_ns; > 0 means NS beat par.
    """

    contract: str | None = None
    declarer: SEAT_NAMES | None = None
    strain: str | None = None
    dd_tricks: int | None = None
    needed: int | None = None
    result: int | None = None
    score_ns: int = 0
    par_ns: int = 0
    vs_par: int = 0

    @classmethod
    def from_history(
        cls, history: BiddingHistory, analysis: DealAnalysis
    ) -> Self:
        """Result of a finished auction (BiddingHistory,
        DealAnalysis of its deal and vulnerability)
        -> ContractResult."""
        par_ns = analysis.par_ns
        contract = history.contract
        if contract is None:
            return cls(par_ns=par_ns, vs_par=-par_ns)

        declarer = contract.declarer
        dd_tricks = analysis.tricks_for(contract.strain, declarer)
        vulnerable = history.vulnerability.is_vulnerable(declarer)
        score = contract.score(dd_tricks, vulnerable)
        score_ns = score if declarer.is_same_side(Seat.NORTH) else -score
        return cls(
            contract=str(contract),
            declarer=declarer.name,
            strain=STRAIN_TO_CHAR[contract.strain],
            dd_tricks=dd_tricks,
            needed=contract.needed,
            result=dd_tricks - contract.needed,
            score_ns=score_ns,
            par_ns=par_ns,
            vs_par=score_ns - par_ns,
        )
