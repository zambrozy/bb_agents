"""Pydantic models for the bidding configuration file."""

import tomllib
from pathlib import Path
from typing import Self, get_args

from pydantic import BaseModel, Field, model_validator

from consts.agents import DEFAULT_MAX_RETRIES, DEFAULT_TIMEOUT
from consts.bidding import CONVENTION
from consts.cards import SEAT_NAMES, Seat


class PlayerConfig(BaseModel):
    """Settings of one player.

    Attributes:
        model (str): Chat model id, e.g. `provider:model-name`, or
            `claude_code:alias` to play through Claude Code.
        convention (CONVENTION): Bidding convention to play.
        timeout (float): Seconds to wait for a model reply.
        max_retries (int): Retries after a failed model request.
        requests_per_minute (float | None): Request limit of the
            model, shared by all seats playing it in this process;
            None for no limit. Ignored by Claude Code players.
    """

    model: str
    convention: CONVENTION
    timeout: float = Field(default=DEFAULT_TIMEOUT, gt=0)
    max_retries: int = Field(default=DEFAULT_MAX_RETRIES, ge=0)
    requests_per_minute: float | None = Field(default=None, gt=0)


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
        for seat in Seat:
            first, second = seat.name, seat.partner.name
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
