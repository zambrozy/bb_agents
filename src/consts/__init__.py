"""Bridge domain constants shared across the sampler module."""

from enum import IntEnum, StrEnum
from typing import Literal


class Suit(IntEnum):
    """Card suit, ordered as DDS expects (0=spades .. 3=clubs)."""

    SPADES = 0
    HEARTS = 1
    DIAMONDS = 2
    CLUBS = 3


class Strain(IntEnum):
    """Contract strain: the four suits plus no-trump."""

    SPADES = 0
    HEARTS = 1
    DIAMONDS = 2
    CLUBS = 3
    NOTRUMP = 4


class Seat(IntEnum):
    """Table seat / player, ordered as DDS expects."""

    NORTH = 0
    EAST = 1
    SOUTH = 2
    WEST = 3


class CallType(StrEnum):
    """Kind of call made during the bidding."""

    PASS = "P"
    BID = "BID"
    DOUBLE = "X"
    REDOUBLE = "XX"


class Vulnerability(IntEnum):
    """Vulnerability codes used by the DDS par calculator."""

    NONE = 0
    BOTH = 1
    NS = 2
    EW = 3


# Card rank bounds: 2 (two) .. 14 (ace).
MIN_RANK = 2
MAX_RANK = 14
CARDS_PER_HAND = 13

# Rank integer -> PBN character.
RANK_TO_CHAR = {
    2: "2", 3: "3", 4: "4", 5: "5", 6: "6", 7: "7", 8: "8",
    9: "9", 10: "T", 11: "J", 12: "Q", 13: "K", 14: "A",
}

# Seat -> PBN seat letter.
SEAT_TO_PBN = {
    Seat.NORTH: "N", Seat.EAST: "E", Seat.SOUTH: "S", Seat.WEST: "W",
}

# Strain -> human-readable contract label.
STRAIN_TO_CHAR = {
    Strain.SPADES: "S", Strain.HEARTS: "H", Strain.DIAMONDS: "D",
    Strain.CLUBS: "C", Strain.NOTRUMP: "NT",
}

# Human-readable contract label -> Strain (inverse of STRAIN_TO_CHAR).
CHAR_TO_STRAIN = {char: strain for strain, char in STRAIN_TO_CHAR.items()}

# Suit -> Unicode symbol for readable deal rendering.
SUIT_TO_SYMBOL = {
    Suit.SPADES: "♠", Suit.HEARTS: "♥",
    Suit.DIAMONDS: "♦", Suit.CLUBS: "♣",
}

# Contract levels a bid may name.
MIN_LEVEL = 1
MAX_LEVEL = 7

# Consecutive passes that close the auction after a bid.
PASSES_TO_END_AFTER_BID = 3
# Calls (all passes) that end an auction with no bid (passed out).
PASSES_TO_END_PASSED_OUT = 4

# Strains from lowest to highest as ranked in the bidding.
BID_STRAIN_ORDER = (
    Strain.CLUBS, Strain.DIAMONDS, Strain.HEARTS,
    Strain.SPADES, Strain.NOTRUMP,
)

SEAT_NAMES = Literal["NORTH", "EAST", "SOUTH", "WEST"]
CONVENTION = Literal["SAYC", "2/1 Force Game"]

CALL_PATTERN = r"^(P|X|XX|[1-7](C|D|H|S|NT))$"
