"""Pydantic model for a bridge hand: the 13 cards of one player."""

from pydantic import BaseModel, field_validator

from consts import (
    CARDS_PER_HAND,
    HCP_BY_RANK,
    PBN_SUIT_SEP,
    RANK_TO_CHAR,
    SUIT_TO_SYMBOL,
    SYMBOL_TO_SUIT,
    VOID_MARK,
    Suit,
)
from models.cards.card import Card


class Hand(BaseModel):
    """A bridge hand: the 13 cards held by one player.

    Attributes:
        cards (list[Card]): Exactly 13 distinct cards.
    """

    cards: list[Card]

    @field_validator("cards")
    @classmethod
    def _check_count(cls, value: list[Card]) -> list[Card]:
        """Ensure a hand holds exactly 13 cards (list[Card])."""
        if len(value) != CARDS_PER_HAND:
            raise ValueError(
                f"hand must have {CARDS_PER_HAND} cards, "
                f"got {len(value)}"
            )
        return value

    @field_validator("cards")
    @classmethod
    def _check_unique(cls, value: list[Card]) -> list[Card]:
        """Ensure no card appears twice in a hand (list[Card])."""
        if len(set(value)) != len(value):
            raise ValueError("hand contains duplicate cards")
        return value

    def suit_ranks(self, suit: Suit) -> list[int]:
        """Return the held ranks in `suit`, highest first (list[int])."""
        return sorted(
            (c.rank for c in self.cards if c.suit == suit),
            reverse=True,
        )

    def suit_chars(self, suit: Suit) -> str:
        """Return the held ranks in `suit` as PBN chars, e.g. 'AKT'
        (str; empty for a void)."""
        return "".join(RANK_TO_CHAR[r] for r in self.suit_ranks(suit))

    @property
    def hcp(self) -> int:
        """High card points: A=4, K=3, Q=2, J=1 (int)."""
        return sum(HCP_BY_RANK.get(c.rank, 0) for c in self.cards)

    def suit_bitmask(self, suit: Suit) -> int:
        """Return the DDS bitmask of held ranks in `suit` (int)."""
        return sum(c.bit for c in self.cards if c.suit == suit)

    def pbn_segment(self) -> str:
        """Return this hand as a PBN body 'S.H.D.C' (str)."""
        return PBN_SUIT_SEP.join(self.suit_chars(suit) for suit in Suit)

    def to_str(self) -> str:
        """Return this hand in readable form (str).

        Example: '♠ AKQ  ♥ T98  ♦ J2  ♣ 5432'; a void is shown as '-'.
        """
        return "  ".join(
            f"{SUIT_TO_SYMBOL[suit]} {self.suit_chars(suit) or VOID_MARK}"
            for suit in Suit
        )

    @classmethod
    def from_str(cls, text: str) -> "Hand":
        """Parse a hand from text (str) -> Hand.

        Two notations are accepted:
        - readable, as produced by `to_str`:
          '♠ AKQ  ♥ T98  ♦ J2  ♣ 5432' (suits in any order,
          '-' or nothing for a void);
        - PBN, as produced by `pbn_segment`: 'AKQ.T98.J2.5432'
          (suits in S, H, D, C order).

        Raises:
            ValueError: If the text is malformed or does not describe
                13 distinct cards.
        """
        if any(symbol in text for symbol in SYMBOL_TO_SUIT):
            cards = cls._parse_readable(text)
        else:
            cards = cls._parse_pbn(text)
        return cls(cards=cards)

    @staticmethod
    def _parse_readable(text: str) -> list[Card]:
        """Parse '♠ AKQ  ♥ T98 ...' into cards (str) -> list[Card]."""
        cards = []
        suit = None
        for char in text:
            if char in SYMBOL_TO_SUIT:
                suit = SYMBOL_TO_SUIT[char]
            elif char.isspace() or char == VOID_MARK:
                continue
            elif suit is None:
                raise ValueError(
                    f"rank {char!r} appears before any suit symbol"
                )
            else:
                cards.append(Card.from_chars(suit, char))
        return cards

    @staticmethod
    def _parse_pbn(text: str) -> list[Card]:
        """Parse 'AKQ.T98.J2.5432' into cards (str) -> list[Card]."""
        segments = text.strip().split(PBN_SUIT_SEP)
        if len(segments) != len(Suit):
            raise ValueError(
                f"PBN hand needs {len(Suit)} suits separated by "
                f"{PBN_SUIT_SEP!r}, got {text!r}"
            )
        return [
            Card.from_chars(suit, char)
            for suit, segment in zip(Suit, segments)
            for char in segment
        ]
