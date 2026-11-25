"""Pydantic model for a full deal: four hands keyed by seat."""

from pydantic import BaseModel, field_validator

from consts.cards import PBN_TO_SEAT, SEAT_TO_PBN, Seat, Suit
from models.cards.hand import Hand


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
