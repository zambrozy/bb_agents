"""Pydantic models for bridge cards, hands, decks, and full deals."""

import random

from pydantic import BaseModel, ConfigDict, Field, field_validator

from consts import (
    CARDS_PER_HAND,
    CHAR_TO_RANK,
    MAX_RANK,
    MIN_RANK,
    PBN_SUIT_SEP,
    PBN_TO_SEAT,
    RANK_TO_CHAR,
    SEAT_TO_PBN,
    SUIT_TO_SYMBOL,
    SYMBOL_TO_SUIT,
    VOID_MARK,
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


class Deal(BaseModel):
    """A full deal: four hands keyed by seat.

    Attributes:
        hands (dict[Seat, Hand]): Hand held by each seat; all four
            seats, no card held twice.
    """

    hands: dict[Seat, Hand]

    @field_validator("hands")
    @classmethod
    def _check_complete(
        cls, value: dict[Seat, Hand]
    ) -> dict[Seat, Hand]:
        """Ensure all four seats are dealt and no card is held by two
        seats (dict[Seat, Hand])."""
        if set(value) != set(Seat):
            missing = [s.name for s in Seat if s not in value]
            raise ValueError(f"deal is missing seats: {missing}")
        cards = [card for hand in value.values() for card in hand.cards]
        if len(set(cards)) != len(cards):
            raise ValueError("deal holds the same card in two hands")
        return value

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

    def to_dict(self) -> dict[str, str]:
        """Return the deal as seat letter -> readable hand text
        (dict[str, str]), e.g. {'N': '♠ AKQ  ♥ T98 ...', ...}."""
        return {
            SEAT_TO_PBN[seat]: self.hands[seat].to_str() for seat in Seat
        }

    def format(self) -> str:
        """Render the deal as one line per seat (str).

        Example line: 'N  ♠ AKQ  ♥ 98  ♦ -  ♣ ...'.
        """
        return "\n".join(
            f"{letter}  {hand}" for letter, hand in self.to_dict().items()
        )

    @classmethod
    def from_dict(cls, data: dict[str, str]) -> "Deal":
        """Parse a deal from seat letter -> hand text (dict) -> Deal.

        Inverse of `to_dict`. Keys are 'N', 'E', 'S', 'W'; each value
        is any notation accepted by `Hand.from_str`.

        Raises:
            ValueError: If a seat is missing, a key is not a seat
                letter, or a hand is malformed.
        """
        unknown = set(data) - set(PBN_TO_SEAT)
        if unknown:
            raise ValueError(f"unknown seat letters: {sorted(unknown)}")
        missing = [
            letter for letter in PBN_TO_SEAT if letter not in data
        ]
        if missing:
            raise ValueError(f"deal is missing seats: {missing}")
        return cls(
            hands={
                PBN_TO_SEAT[letter]: Hand.from_str(text)
                for letter, text in data.items()
            }
        )


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
