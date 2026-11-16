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


# Vulnerability -> wording shown to the players.
VULNERABILITY_TEXT = {
    Vulnerability.NONE: "Neither side vulnerable",
    Vulnerability.BOTH: "Both sides vulnerable",
    Vulnerability.NS: "North-South vulnerable",
    Vulnerability.EW: "East-West vulnerable",
}

# Card rank bounds: 2 (two) .. 14 (ace).
MIN_RANK = 2
MAX_RANK = 14
CARDS_PER_HAND = 13

# High card points per rank: ace 4, king 3, queen 2, jack 1.
HCP_BY_RANK = {14: 4, 13: 3, 12: 2, 11: 1}

# Tricks the declarer needs on top of the contract level (the book).
BOOK_TRICKS = 6

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

# Unicode suit symbol -> Suit (inverse of SUIT_TO_SYMBOL).
SYMBOL_TO_SUIT = {symbol: suit for suit, symbol in SUIT_TO_SYMBOL.items()}

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

SEAT_NAMES = Literal["NORTH", "EAST", "SOUTH", "WEST"]
VULNERABILITY_NAMES = Literal["NONE", "BOTH", "NS", "EW"]
CONVENTION = Literal["SAYC", "2/1 Force Game"]

CALL_PATTERN = r"^(P|X|XX|[1-7](C|D|H|S|NT))$"

# Model request limits: seconds to wait for a reply, retries after a
# failed request.
DEFAULT_TIMEOUT = 60.0
DEFAULT_MAX_RETRIES = 1

# Claude Code players: CLI binary and the model-string prefix that
# selects it, e.g. "claude_code:sonnet".
CLAUDE_BIN = "claude"
CLAUDE_CODE_PREFIX = "claude_code:"

# Default location of the players config, relative to the project root.
DEFAULT_CONFIG_PATH = "config/bidding.toml"
