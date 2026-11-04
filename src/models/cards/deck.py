"""Pydantic model for a deck of cards and the standard 52-card deck."""

import random

from pydantic import BaseModel, ConfigDict, field_validator

from consts import CARDS_PER_HAND, MAX_RANK, MIN_RANK, Seat, Suit
from models.cards.card import Card
from models.cards.deal import Deal
from models.cards.hand import Hand


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

    def deal(self, rng: random.Random) -> Deal:
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
