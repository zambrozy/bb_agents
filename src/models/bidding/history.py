"""Pydantic model for the record of calls in one auction."""

from pydantic import BaseModel, Field

from consts import (
    BID_STRAIN_ORDER,
    MAX_LEVEL,
    MIN_LEVEL,
    NO_CALL_MARK,
    PASSES_TO_END_AFTER_BID,
    PASSES_TO_END_PASSED_OUT,
    SEAT_TO_PBN,
    TABLE_COL_WIDTH,
    CallType,
    Seat,
    Vulnerability
)
from models.bidding.call import Call
from models.bidding.contract import Contract


def _partners(a: Seat, b: Seat) -> bool:
    """Whether seats are on one side (a: Seat, b: Seat) -> bool."""
    return a % 2 == b % 2


class BiddingHistory(BaseModel):
    """Ordered calls of an auction, starting from the dealer.

    Mutable: `add` appends a call in place after checking legality.

    Attributes:
        dealer (Seat): Seat that makes the first call.
        vulnerability (Vulnerability): deal vulnerability
        calls (list[Call]): Calls made so far, in order.
    """

    dealer: Seat
    vulnerability: Vulnerability
    calls: list[Call] = Field(default_factory=list)

    def seat_of(self, index: int) -> Seat:
        """Seat that made call number `index` (int) -> Seat."""
        return Seat((self.dealer + index) % len(Seat))

    @property
    def next_seat(self) -> Seat:
        """Seat due to call next (Seat)."""
        return self.seat_of(len(self.calls))

    def _last_index(self, bids_only: bool) -> int | None:
        """Index of the latest bid, or latest non-pass if not
        `bids_only`; None if absent (bool) -> int | None."""
        for i in range(len(self.calls) - 1, -1, -1):
            call = self.calls[i]
            if call.is_bid or (
                not bids_only and call.kind != CallType.PASS
            ):
                return i
        return None

    @property
    def is_over(self) -> bool:
        """Whether the auction has ended (bool)."""
        if self._last_index(bids_only=True) is None:
            return len(self.calls) >= PASSES_TO_END_PASSED_OUT
        tail = self.calls[-PASSES_TO_END_AFTER_BID:]
        return len(tail) == PASSES_TO_END_AFTER_BID and all(
            c.kind == CallType.PASS for c in tail
        )

    def is_legal(self, call: Call) -> bool:
        """Whether `call` is legal for the next seat (Call) -> bool."""
        if self.is_over:
            # No call is allowed once the auction has ended.
            return False
        elif call.kind == CallType.PASS:
            # A pass is always allowed while the auction runs.
            return True
        elif call.is_bid:
            # A bid must outrank the latest bid (any bid opens).
            bid_index = self._last_index(bids_only=True)
            return bid_index is None or (
                call.rank > self.calls[bid_index].rank
            )
        else:
            # Double / redouble: react to the latest non-pass call.
            last = self._last_index(bids_only=False)
            if last is None:
                # Nothing to double or redouble yet.
                return False
            # Double targets a bid; redouble targets a double.
            wanted = (
                CallType.BID if call.kind == CallType.DOUBLE
                else CallType.DOUBLE
            )
            # That call must have been made by an opponent.
            opponent = not _partners(self.seat_of(last), self.next_seat)
            return opponent and self.calls[last].kind == wanted

    def legal_calls(self) -> list[Call]:
        """All legal calls for the next seat (-> list[Call])."""
        if self.is_over:
            return []
        candidates = [
            Call.make_pass(), Call.double(), Call.redouble(),
        ] + [
            Call.bid(level, strain)
            for level in range(MIN_LEVEL, MAX_LEVEL + 1)
            for strain in BID_STRAIN_ORDER
        ]
        return [c for c in candidates if self.is_legal(c)]

    def add(self, call: Call) -> None:
        """Append `call` in place (Call) -> None.

        Raises:
            ValueError: If the auction is over or the call is illegal.
        """
        if self.is_over:
            raise ValueError("the auction is already over")
        if not self.is_legal(call):
            raise ValueError(
                f"illegal call {call} for {self.next_seat.name}"
            )
        self.calls.append(call)

    def to_table(self) -> str:
        """Auction as a table with a seat header, one round per row
        (-> str).

        Seats before the dealer are shown as `-`.
        """
        cells = [NO_CALL_MARK] * self.dealer
        cells += [str(call) for call in self.calls]
        rows = [[SEAT_TO_PBN[seat] for seat in Seat]]
        rows += [
            cells[i:i + len(Seat)] for i in range(0, len(cells), len(Seat))
        ]
        return "\n".join(
            " ".join(cell.ljust(TABLE_COL_WIDTH) for cell in row).rstrip()
            for row in rows
        )

    @property
    def contract(self) -> Contract | None:
        """Final contract; None if not over or passed out
        (-> Contract | None)."""
        bid_index = self._last_index(bids_only=True)
        if not self.is_over or bid_index is None:
            return None
        final = self.calls[bid_index]
        bidder = self.seat_of(bid_index)
        declarer = bidder
        for i, call in enumerate(self.calls):
            if (
                call.is_bid
                and call.strain == final.strain
                and _partners(self.seat_of(i), bidder)
            ):
                declarer = self.seat_of(i)
                break
        after = [c.kind for c in self.calls[bid_index + 1:]]
        return Contract(
            level=final.level,
            strain=final.strain,
            declarer=declarer,
            doubled=CallType.DOUBLE in after,
            redoubled=CallType.REDOUBLE in after,
        )
