"""Pydantic models for bridge cards, hands, decks, and full deals."""

import random

from pydantic import BaseModel, ConfigDict, Field, field_validator

from consts import (
    CARDS_PER_HAND,
    MAX_RANK,
    MIN_RANK,
    RANK_TO_CHAR,
    Seat,
    Suit,
)


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


class Hand(BaseModel):
    """A bridge hand: the 13 cards held by one player.

    Attributes:
        cards (list[Card]): Exactly 13 cards.
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

    def suit_bitmask(self, suit: Suit) -> int:
        """Return the DDS bitmask of held ranks in `suit` (int)."""
        return sum(c.bit for c in self.cards if c.suit == suit)

    def pbn_segment(self) -> str:
        """Return this hand as a PBN body 'S.H.D.C' (str)."""
        parts = []
        for suit in Suit:
            ranks = sorted(
                (c.rank for c in self.cards if c.suit == suit),
                reverse=True,
            )
            parts.append("".join(RANK_TO_CHAR[r] for r in ranks))
        return ".".join(parts)


class Deal(BaseModel):
    """A full deal: four hands keyed by seat.

    Attributes:
        hands (dict[Seat, Hand]): Hand held by each seat.
    """

    hands: dict[Seat, Hand]

    def to_pbn(self) -> str:
        """Render the deal as a PBN string (str).

        Hands are listed clockwise from North, which is the form DDS
        expects; who leads/declares is a separate solver argument.

        Returns:
            str: 'N:<north> <east> <south> <west>'.
        """
        body = " ".join(self.hands[s].pbn_segment() for s in Seat)
        return f"N:{body}"

    def to_bitmask(self) -> list[list[int]]:
        """Return the 4x4 [seat][suit] bitmask array for DDS (list)."""
        return [
            [self.hands[seat].suit_bitmask(suit) for suit in Suit]
            for seat in Seat
        ]


class Deck(BaseModel):
    """A collection of distinct bridge cards.

    Attributes:
        cards (tuple[Card, ...]): The cards held by the deck.
    """

    model_config = ConfigDict(frozen=True)

    cards: tuple[Card, ...]

    @field_validator("cards")
    @classmethod
    def _check_distinct(
        cls, value: tuple[Card, ...]
    ) -> tuple[Card, ...]:
        """Reject decks with duplicate cards (tuple[Card, ...])."""
        if len(set(value)) != len(value):
            raise ValueError("deck contains duplicate cards")
        return value

    @classmethod
    def standard(cls) -> "Deck":
        """Build the canonical 52-card deck (Deck)."""
        return cls(
            cards=tuple(
                Card(suit=suit, rank=rank)
                for suit in Suit
                for rank in range(MIN_RANK, MAX_RANK + 1)
            )
        )

    def deal(self, rng: random.Random) -> "Deal":
        """Shuffle with `rng` and split into four hands.

        Args:
            rng (random.Random): Source of shuffle randomness.

        Returns:
            Deal: 13 cards per seat, dealt clockwise from North.
        """
        cards = list(self.cards)
        rng.shuffle(cards)
        hands = {
            seat: Hand(
                cards=cards[i * CARDS_PER_HAND:(i + 1) * CARDS_PER_HAND]
            )
            for i, seat in enumerate(Seat)
        }
        return Deal(hands=hands)


# The canonical 52-card deck, built once at import and reused across
# deals (cards are immutable, so sharing them between deals is safe).
STANDARD_DECK: Deck = Deck.standard()
