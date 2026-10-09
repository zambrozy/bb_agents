"""Pydantic model for the contract an auction ends in."""

from pydantic import BaseModel, ConfigDict

from consts import STRAIN_TO_CHAR, Seat, Strain


class Contract(BaseModel):
    """Final contract of a completed auction.

    Attributes:
        level (int): Contract level 1..7.
        strain (Strain): Contract strain.
        declarer (Seat): Seat that will play the contract.
        doubled (bool): Whether the contract is doubled.
        redoubled (bool): Whether the contract is redoubled.
    """

    model_config = ConfigDict(frozen=True)

    level: int
    strain: Strain
    declarer: Seat
    doubled: bool = False
    redoubled: bool = False

    def __str__(self) -> str:
        """Text such as `4H X by NORTH` (str)."""
        mark = " XX" if self.redoubled else " X" if self.doubled else ""
        text = f"{self.level}{STRAIN_TO_CHAR[self.strain]}{mark}"
        return f"{text} by {self.declarer.name}"
