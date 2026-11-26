"""Pydantic models for double-dummy deal analysis results."""

from pydantic import BaseModel

from consts.bidding import STRAIN_TO_CHAR, Strain
from consts.cards import SEAT_TO_PBN, Seat


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

    @classmethod
    def from_dds(cls, table: dict, par: dict) -> "DealAnalysis":
        """Build an analysis from raw DDS results (dict, dict)
        -> DealAnalysis.

        Args:
            table (dict): Output of `dds3.calc_dd_table`; its
                'res_table' is indexed [strain][seat].
            par (dict): Output of `dds3.par` for that table.
        """
        res = table["res_table"]
        return cls(
            tricks={
                strain: {seat: res[strain][seat] for seat in Seat}
                for strain in Strain
            },
            par_score=par["par_score"],
            par_contracts=par["par_contracts_string"],
        )

    @property
    def par_ns(self) -> int:
        """Par score from North-South's view, e.g. 1510 for
        'NS 1510' (int)."""
        return int(self.par_score[0].split()[-1])

    def tricks_for(self, strain: Strain, declarer: Seat) -> int:
        """Tricks available for `declarer` in `strain` (int)."""
        return self.tricks[strain][declarer]

    def format(self) -> str:
        """Render double-dummy tricks and par as a table (str).

        Returns:
            str: A strain-by-seat trick table plus par lines.
        """
        header = f"{'':>6}" + "".join(
            f"{SEAT_TO_PBN[seat]:>4}" for seat in Seat
        )
        rows = [header]
        for strain in Strain:
            cells = "".join(
                f"{self.tricks_for(strain, seat):>4}" for seat in Seat
            )
            rows.append(f"{STRAIN_TO_CHAR[strain]:>4}  {cells}")

        return (
            "\n".join(rows)
            + f"\n\nPar score:    {self.par_score}"
            + f"\nPar contract: {self.par_contracts}"
        )
