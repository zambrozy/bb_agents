"""Constants of the auction: strains, calls, levels and rules."""

from enum import IntEnum, StrEnum
from typing import Literal


class Strain(IntEnum):
    """Contract strain: the four suits plus no-trump."""

    SPADES = 0
    HEARTS = 1
    DIAMONDS = 2
    CLUBS = 3
    NOTRUMP = 4


class CallType(StrEnum):
    """Kind of call made during the bidding."""

    PASS = "P"
    BID = "BID"
    DOUBLE = "X"
    REDOUBLE = "XX"


# Tricks the declarer needs on top of the contract level (the book).
BOOK_TRICKS = 6

# Strain -> human-readable contract label.
STRAIN_TO_CHAR = {
    Strain.SPADES: "S", Strain.HEARTS: "H", Strain.DIAMONDS: "D",
    Strain.CLUBS: "C", Strain.NOTRUMP: "NT",
}

# Human-readable contract label -> Strain (inverse of STRAIN_TO_CHAR).
CHAR_TO_STRAIN = {char: strain for strain, char in STRAIN_TO_CHAR.items()}

# Auction table rendering: column width and mark for "no call yet".
TABLE_COL_WIDTH = 4
NO_CALL_MARK = "-"

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

# Bidding systems a player may be configured with.
CONVENTION = Literal["SAYC", "2/1 Force Game"]

# A valid call string: pass, double, redouble or a bid like "4H".
CALL_PATTERN = r"^(P|X|XX|[1-7](C|D|H|S|NT))$"
