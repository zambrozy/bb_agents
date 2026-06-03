"""Sampling and double-dummy analysis of bridge deals."""

import random

import dds3

from consts import (
    SEAT_TO_PBN,
    STRAIN_TO_CHAR,
    SUIT_TO_SYMBOL,
    Seat,
    Strain,
    Suit,
    Vulnerability,
)
from models.sampler.analysis import DealAnalysis
from models.sampler.cards import STANDARD_DECK, Deal


class DealSampler:
    """Samples random bridge deals and analyzes them with DDS.

    Args:
        seed (int | None): Optional seed for reproducible shuffles.
    """

    def __init__(self, seed: int | None = None) -> None:
        self._rng = random.Random(seed)

    def sample_deal(self) -> Deal:
        """Deal a freshly shuffled standard deck.

        Returns:
            Deal: A random deal with 13 cards per seat.
        """
        return STANDARD_DECK.deal(self._rng)

    def analyze(
        self,
        deal: Deal,
        vulnerable: Vulnerability = Vulnerability.NONE,
    ) -> DealAnalysis:
        """Compute double-dummy tricks and par for a deal.

        Args:
            deal (Deal): The deal to analyze.
            vulnerable (Vulnerability): Vulnerability for par scoring.

        Returns:
            DealAnalysis: Per-strain/seat trick counts and par.
        """
        table = dds3.calc_dd_table({"cards": deal.to_bitmask()})
        res = table["res_table"]
        tricks = {
            strain: {
                seat: res[int(strain)][int(seat)] for seat in Seat
            }
            for strain in Strain
        }
        par_result = dds3.par(table, vulnerable=int(vulnerable))
        return DealAnalysis(
            tricks=tricks,
            par_score=par_result["par_score"],
            par_contracts=par_result["par_contracts_string"],
        )

    def sample_and_analyze(
        self,
        vulnerable: Vulnerability = Vulnerability.NONE,
    ) -> tuple[Deal, DealAnalysis]:
        """Sample one deal and return it with its analysis.

        Args:
            vulnerable (Vulnerability): Vulnerability for par scoring.

        Returns:
            tuple[Deal, DealAnalysis]: The deal and its analysis.
        """
        deal = self.sample_deal()
        return deal, self.analyze(deal, vulnerable=vulnerable)

    @staticmethod
    def format_deal(deal: Deal) -> str:
        """Render a deal as a readable per-seat listing.

        Args:
            deal (Deal): The deal to render.

        Returns:
            str: One line per seat, e.g. 'N  ♠ AKQ  ♥ 98 ...'.
        """
        lines = []
        for seat in Seat:
            segments = deal.hands[seat].pbn_segment().split(".")
            suits = "  ".join(
                f"{SUIT_TO_SYMBOL[suit]} {ranks or '-'}"
                for suit, ranks in zip(Suit, segments)
            )
            lines.append(f"{SEAT_TO_PBN[seat]}  {suits}")
        return "\n".join(lines)

    @staticmethod
    def format_analysis(analysis: DealAnalysis) -> str:
        """Render double-dummy tricks and par as a table.

        Args:
            analysis (DealAnalysis): The analysis to render.

        Returns:
            str: A strain-by-seat trick table plus par lines.
        """
        header = f"{'':>6}" + "".join(
            f"{SEAT_TO_PBN[seat]:>4}" for seat in Seat
        )
        rows = [header]
        for strain in Strain:
            cells = "".join(
                f"{analysis.tricks_for(strain, seat):>4}"
                for seat in Seat
            )
            rows.append(f"{STRAIN_TO_CHAR[strain]:>4}  {cells}")

        return (
            "\n".join(rows)
            + f"\n\nPar score:    {analysis.par_score}"
            + f"\nPar contract: {analysis.par_contracts}"
        )

    @staticmethod
    def format_report(deal: Deal, analysis: DealAnalysis) -> str:
        """Combine PBN, hand layout, and analysis into one report.

        Args:
            deal (Deal): The deal to render.
            analysis (DealAnalysis): Its double-dummy analysis.

        Returns:
            str: A multi-section, human-readable report.
        """
        return (
            f"PBN: {deal.to_pbn()}\n\n"
            f"{DealSampler.format_deal(deal)}\n\n"
            f"{DealSampler.format_analysis(analysis)}"
        )
