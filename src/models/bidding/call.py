"""Pydantic model for a single call made during the bidding."""

from typing import Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from consts import (
    BID_STRAIN_ORDER,
    MAX_LEVEL,
    MIN_LEVEL,
    STRAIN_TO_CHAR,
    CallType,
    Strain,
)


class Call(BaseModel):
    """One call: a bid, pass, double or redouble.

    Immutable value object. Only bids carry a level and a strain.

    Attributes:
        kind (CallType): Type of the call.
        level (int | None): Bid level 1..7; None unless a bid.
        strain (Strain | None): Bid strain; None unless a bid.
    """

    model_config = ConfigDict(frozen=True)

    kind: CallType
    level: int | None = Field(default=None, ge=MIN_LEVEL, le=MAX_LEVEL)
    strain: Strain | None = None

    @model_validator(mode="after")
    def _check_fields(self) -> Self:
        """Require level and strain exactly for bids (Self)."""
        is_bid = self.kind == CallType.BID
        has_both = self.level is not None and self.strain is not None
        has_none = self.level is None and self.strain is None
        if is_bid and not has_both:
            raise ValueError("a bid needs a level and a strain")
        if not is_bid and not has_none:
            raise ValueError("only a bid has a level and a strain")
        return self

    @classmethod
    def bid(cls, level: int, strain: Strain) -> Self:
        """Build a bid (level: int, strain: Strain) -> Call."""
        return cls(kind=CallType.BID, level=level, strain=strain)

    @classmethod
    def make_pass(cls) -> Self:
        """Build a pass (-> Call)."""
        return cls(kind=CallType.PASS)

    @classmethod
    def double(cls) -> Self:
        """Build a double (-> Call)."""
        return cls(kind=CallType.DOUBLE)

    @classmethod
    def redouble(cls) -> Self:
        """Build a redouble (-> Call)."""
        return cls(kind=CallType.REDOUBLE)

    @property
    def is_bid(self) -> bool:
        """Whether this call is a bid (bool)."""
        return self.kind == CallType.BID

    @property
    def rank(self) -> int:
        """Bid strength for comparison, higher outranks (int).

        Raises:
            ValueError: If the call is not a bid.
        """
        if not self.is_bid:
            raise ValueError("only a bid has a rank")
        step = BID_STRAIN_ORDER.index(self.strain)
        return self.level * len(BID_STRAIN_ORDER) + step

    def __str__(self) -> str:
        """Short text such as `1NT`, `P`, `X`, `XX` (str)."""
        if self.is_bid:
            return f"{self.level}{STRAIN_TO_CHAR[self.strain]}"
        return self.kind.value
