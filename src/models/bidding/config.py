"""Pydantic models for the bidding configuration file."""

import tomllib
from pathlib import Path
from typing import Self, get_args

from pydantic import BaseModel, model_validator

from consts import CONVENTION, PARTNER_SEATS, SEAT_NAMES


class PlayerConfig(BaseModel):
    """Settings of one player.

    Attributes:
        model (str): Chat model id, e.g. `provider:model-name`.
        convention (CONVENTION): Bidding convention to play.
    """

    model: str
    convention: CONVENTION


class BiddingConfig(BaseModel):
    """Settings of all four players.

    Attributes:
        players (dict[SEAT_NAMES, PlayerConfig]): Player per seat.
    """

    players: dict[SEAT_NAMES, PlayerConfig]

    @model_validator(mode="after")
    def _check_players(self) -> Self:
        """Require every seat, and one convention per partnership
        (Self)."""
        missing = set(get_args(SEAT_NAMES)) - set(self.players)
        if missing:
            raise ValueError(f"missing players: {sorted(missing)}")
        for first, second in PARTNER_SEATS:
            if (
                self.players[first].convention
                != self.players[second].convention
            ):
                raise ValueError(
                    f"{first} and {second} must play one convention"
                )
        return self

    @classmethod
    def load(cls, path: str | Path) -> Self:
        """Read a TOML file (path: str | Path) -> BiddingConfig.

        Raises:
            FileNotFoundError: If the file does not exist.
            ValueError: If the content is not a valid config.
        """
        with open(path, "rb") as file:
            return cls.model_validate(tomllib.load(file))
