"""Constants of cards, hands and deals (shared by sampler and bidding)."""

from enum import IntEnum
from typing import Literal


class Suit(IntEnum):
    """Card suit, ordered as DDS expects (0=spades .. 3=clubs)."""

    SPADES = 0
    HEARTS = 1
    DIAMONDS = 2
    CLUBS = 3


class Seat(IntEnum):
    """Table seat / player, ordered as DDS expects."""

    NORTH = 0
    EAST = 1
    SOUTH = 2
    WEST = 3

    @property
    def partner(self) -> "Seat":
        """Seat across the table (Seat)."""
        return Seat((self + 2) % len(Seat))

    @property
    def opponents(self) -> tuple["Seat", "Seat"]:
        """The two seats of the other side, in seat order
        (tuple[Seat, Seat])."""
        return tuple(s for s in Seat if not self.is_same_side(s))

    def is_same_side(self, other: "Seat") -> bool:
        """Whether `other` is this seat or its partner (Seat) -> bool."""
        return self % 2 == other % 2


class Vulnerability(IntEnum):
    """Vulnerability codes used by the DDS par calculator."""

    NONE = 0
    BOTH = 1
    NS = 2
    EW = 3


# Vulnerability -> wording shown to the players.
VULNERABILITY_TEXT = {
    Vulnerability.NONE: "Neither side vulnerable",
    Vulnerability.BOTH: "Both sides vulnerable",
    Vulnerability.NS: "North-South vulnerable",
    Vulnerability.EW: "East-West vulnerable",
}

# Enum member names, as accepted in configs and API payloads.
SEAT_NAMES = Literal["NORTH", "EAST", "SOUTH", "WEST"]
VULNERABILITY_NAMES = Literal["NONE", "BOTH", "NS", "EW"]

# Card rank bounds: 2 (two) .. 14 (ace).
MIN_RANK = 2
MAX_RANK = 14
CARDS_PER_HAND = 13

# High card points per rank: ace 4, king 3, queen 2, jack 1.
HCP_BY_RANK = {14: 4, 13: 3, 12: 2, 11: 1}

# Rank integer -> PBN character.
RANK_TO_CHAR = {
    2: "2", 3: "3", 4: "4", 5: "5", 6: "6", 7: "7", 8: "8",
    9: "9", 10: "T", 11: "J", 12: "Q", 13: "K", 14: "A",
}

# PBN character -> rank integer (inverse of RANK_TO_CHAR).
CHAR_TO_RANK = {char: rank for rank, char in RANK_TO_CHAR.items()}

# Seat -> PBN seat letter.
SEAT_TO_PBN = {
    Seat.NORTH: "N", Seat.EAST: "E", Seat.SOUTH: "S", Seat.WEST: "W",
}

# PBN seat letter -> Seat (inverse of SEAT_TO_PBN).
PBN_TO_SEAT = {letter: seat for seat, letter in SEAT_TO_PBN.items()}

# PBN hand notation: suit separator ('AKQ.T98.J2.5432').
PBN_SUIT_SEP = "."
# Readable hand notation: shown in place of the ranks of a void suit.
VOID_MARK = "-"

# Suit -> Unicode symbol for readable deal rendering.
SUIT_TO_SYMBOL = {
    Suit.SPADES: "♠", Suit.HEARTS: "♥",
    Suit.DIAMONDS: "♦", Suit.CLUBS: "♣",
}

# Unicode suit symbol -> Suit (inverse of SUIT_TO_SYMBOL).
SYMBOL_TO_SUIT = {symbol: suit for suit, symbol in SUIT_TO_SYMBOL.items()}
