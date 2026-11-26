"""Pydantic model for the contract an auction ends in."""

from pydantic import BaseModel, ConfigDict

from consts.bidding import (
    BOOK_TRICKS,
    DOUBLED_FACTOR,
    DOUBLED_INSULT_BONUS,
    DOUBLED_OVERTRICK,
    DOUBLED_UNDERTRICKS,
    GAME_BONUS,
    GAME_POINTS,
    NT_FIRST_TRICK_EXTRA,
    PART_SCORE_BONUS,
    REDOUBLED_FACTOR,
    REDOUBLED_INSULT_BONUS,
    REDOUBLED_OVERTRICK,
    REDOUBLED_UNDERTRICKS,
    SLAM_BONUS,
    STRAIN_TO_CHAR,
    TRICK_POINTS,
    UNDOUBLED_UNDERTRICKS,
    Strain,
)
from consts.cards import Seat


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

    @property
    def needed(self) -> int:
        """Tricks the declarer must take to make the contract
        (int)."""
        return self.level + BOOK_TRICKS

    def score(self, tricks: int, vulnerable: bool) -> int:
        """Duplicate score of the declarer's side (tricks: taken by
        the declarer, vulnerable: whether the declarer is) -> int;
        negative when the contract goes down."""
        over = tricks - self.needed
        if over < 0:
            return -self._penalty(-over, vulnerable)
        return self._made_score(over, vulnerable)

    def _penalty(self, down: int, vulnerable: bool) -> int:
        """Penalty for `down` undertricks (int, bool) -> int > 0."""
        if self.redoubled:
            table = REDOUBLED_UNDERTRICKS[vulnerable]
        elif self.doubled:
            table = DOUBLED_UNDERTRICKS[vulnerable]
        else:
            table = UNDOUBLED_UNDERTRICKS[vulnerable]
        last = len(table) - 1
        return sum(table[min(i, last)] for i in range(down))

    def _made_score(self, over: int, vulnerable: bool) -> int:
        """Score of a made contract with `over` overtricks
        (int, bool) -> int >= 0."""
        factor = 1
        if self.redoubled:
            factor = REDOUBLED_FACTOR
        elif self.doubled:
            factor = DOUBLED_FACTOR
        trick_points = TRICK_POINTS[self.strain]
        points = self.level * trick_points
        if self.strain == Strain.NOTRUMP:
            points += NT_FIRST_TRICK_EXTRA
        points *= factor

        score = points
        if points >= GAME_POINTS:
            score += GAME_BONUS[vulnerable]
        else:
            score += PART_SCORE_BONUS
        score += SLAM_BONUS.get(self.level, {}).get(vulnerable, 0)

        if self.redoubled:
            score += REDOUBLED_INSULT_BONUS
            score += over * REDOUBLED_OVERTRICK[vulnerable]
        elif self.doubled:
            score += DOUBLED_INSULT_BONUS
            score += over * DOUBLED_OVERTRICK[vulnerable]
        else:
            score += over * trick_points
        return score

    def __str__(self) -> str:
        """Text such as `4H X by NORTH` (str)."""
        mark = " XX" if self.redoubled else " X" if self.doubled else ""
        text = f"{self.level}{STRAIN_TO_CHAR[self.strain]}{mark}"
        return f"{text} by {self.declarer.name}"
