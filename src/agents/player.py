from langchain.chat_models import init_chat_model
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import Runnable

from models.bidding.call import PlayerReply
from agents.player_claude_code import create_claude_code_player
from consts.agents import (
    CLAUDE_CODE_PREFIX,
    DEFAULT_MAX_RETRIES,
    DEFAULT_TIMEOUT,
)
from consts.bidding import CONVENTION
from consts.cards import SEAT_NAMES, Seat

system_prompt = """
You are the bridge player at seat {seat}. Your partner is {partner}. \
Your opponents are {opponents}.
Your task is to take part in a bidding stage of a game. Each turn you \
receive your hand, the dealer, the vulnerability, the auction so far and \
Your previous thoughts. You have to decide what to bid on your turn.
Use {convention} bidding convention.
"""

# Sections of the user message sent to a player on each turn.
TURN_PROMPT = """\
Dealer: {dealer}
Vulnerability: {vulnerability}
Your hand: {hand}

Auction so far (in order):
{auction}

Your earlier reasoning:
{reasoning}
"""

REJECTED_PROMPT = """
Your previous attempt was REJECTED as an illegal call. Choose again.
Rejected call: {call}
Reasoning behind it:
{reasoning}
"""

NO_REASONING = "(none yet)"
NO_CALLS = "(no calls yet)"


def create_player(
    model_name: str,
    seat: SEAT_NAMES,
    convention: CONVENTION,
    timeout: float = DEFAULT_TIMEOUT,
    max_retries: int = DEFAULT_MAX_RETRIES,
) -> Runnable[dict[str, str], PlayerReply]:
    """Build a player (model_name: `provider:model`, or
    `claude_code:alias` for Claude Code; seat, convention,
    timeout: seconds per reply, max_retries: int)
    -> runnable taking {"turn": str} and returning a PlayerReply."""
    table_seat = Seat[seat]
    system = system_prompt.format(
        seat=seat,
        partner=table_seat.partner.name,
        opponents=" and ".join(s.name for s in table_seat.opponents),
        convention=convention,
    )
    if model_name.startswith(CLAUDE_CODE_PREFIX):
        return create_claude_code_player(
            model_name.removeprefix(CLAUDE_CODE_PREFIX),
            system, timeout, max_retries,
        )

    model = init_chat_model(
        model_name, timeout=timeout, max_retries=max_retries
    ).with_structured_output(PlayerReply)
    prompt = ChatPromptTemplate.from_messages([
        ("system", system),
        ("human", "{turn}"),
    ])

    return prompt | model



