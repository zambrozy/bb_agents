"""Pydantic model for a single playing card."""

from pydantic import BaseModel, ConfigDict, Field

from consts import CHAR_TO_RANK, MAX_RANK, MIN_RANK, Suit


class Card(BaseModel):
    """A single playing card.

    Immutable value object, so one instance can be shared safely
    across many deals.

    Attributes:
        suit (Suit): One of the four suits.
        rank (int): Rank value, 2 (two) .. 14 (ace).
    """

    model_config = ConfigDict(frozen=True)

    suit: Suit
    rank: int = Field(ge=MIN_RANK, le=MAX_RANK)

    @property
    def bit(self) -> int:
        """DDS rank bitmask for this card (int)."""
        return 1 << self.rank

    @classmethod
    def from_chars(cls, suit: Suit, rank_char: str) -> "Card":
        """Build a card from a suit and a PBN rank char, e.g. 'T'.

        Args:
            suit (Suit): Suit of the card.
            rank_char (str): Rank character, '2'..'9', T, J, Q, K, A
                (case-insensitive).

        Returns:
            Card: The parsed card.

        Raises:
            ValueError: If `rank_char` is not a rank character.
        """
        rank = CHAR_TO_RANK.get(rank_char.upper())
        if rank is None:
            raise ValueError(f"unknown rank character {rank_char!r}")
        return cls(suit=suit, rank=rank)
