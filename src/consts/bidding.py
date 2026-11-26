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

# --- Duplicate scoring --------------------------------------------
# Dicts keyed by bool are indexed by "declarer is vulnerable".

# Points per contracted trick, undoubled; the first NT trick gets
# NT_FIRST_TRICK_EXTRA on top (40, then 30 each).
TRICK_POINTS = {
    Strain.CLUBS: 20, Strain.DIAMONDS: 20,
    Strain.HEARTS: 30, Strain.SPADES: 30, Strain.NOTRUMP: 30,
}
NT_FIRST_TRICK_EXTRA = 10

# Contracted trick points multipliers of a doubled / redoubled
# contract.
DOUBLED_FACTOR = 2
REDOUBLED_FACTOR = 4

# Contracted trick points that make a game.
GAME_POINTS = 100
PART_SCORE_BONUS = 50
GAME_BONUS = {False: 300, True: 500}

# Slam level -> bonus by vulnerability.
SMALL_SLAM_LEVEL = 6
GRAND_SLAM_LEVEL = 7
SLAM_BONUS = {
    SMALL_SLAM_LEVEL: {False: 500, True: 750},
    GRAND_SLAM_LEVEL: {False: 1000, True: 1500},
}

# Bonus for making a doubled / redoubled contract (the "insult").
DOUBLED_INSULT_BONUS = 50
REDOUBLED_INSULT_BONUS = 100

# Points per overtrick of a doubled / redoubled contract (undoubled
# overtricks score as contracted tricks: TRICK_POINTS).
DOUBLED_OVERTRICK = {False: 100, True: 200}
REDOUBLED_OVERTRICK = {False: 200, True: 400}

# Undertrick penalties: penalty of the 1st, 2nd, 3rd, 4th and every
# later undertrick.
UNDOUBLED_UNDERTRICKS = {
    False: (50, 50, 50, 50),
    True: (100, 100, 100, 100),
}
DOUBLED_UNDERTRICKS = {
    False: (100, 200, 200, 300),
    True: (200, 300, 300, 300),
}
REDOUBLED_UNDERTRICKS = {
    False: (200, 400, 400, 600),
    True: (400, 600, 600, 600),
}
