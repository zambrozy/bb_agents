"""Sampling and double-dummy analysis of bridge deals."""

import random

import dds3

from consts import Vulnerability
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
        par = dds3.par(table, vulnerable=int(vulnerable))
        return DealAnalysis.from_dds(table, par)

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
            f"{deal.format()}\n\n"
            f"{analysis.format()}"
        )
