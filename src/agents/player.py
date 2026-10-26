from langchain.chat_models import init_chat_model
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import Runnable

from models.bidding.call import PlayerReply
from consts import (
    CONVENTION,
    DEFAULT_MAX_RETRIES,
    DEFAULT_TIMEOUT,
    SEAT_NAMES,
)

system_prompt = """
You are a bridge player on {side} side. Your task is to take part in a bidding stage of a game.
You receive auction history and Your previous thoughts. You have to decide what to bid on your turn.
Use {convention} bidding convention.
"""

# Sections of the user message sent to a player on each turn.
TURN_PROMPT = """\
Your seat: {seat}
Your hand: {hand}

Auction so far:
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


def create_player(
    model_name: str,
    side: SEAT_NAMES,
    convention: CONVENTION,
    timeout: float = DEFAULT_TIMEOUT,
    max_retries: int = DEFAULT_MAX_RETRIES,
) -> Runnable[dict[str, str], PlayerReply]:
    """Build a player (model_name: `provider:model`, side, convention,
    timeout: seconds per reply, max_retries: int)
    -> runnable taking {"turn": str} and returning a PlayerReply."""
    model = init_chat_model(
        model_name, timeout=timeout, max_retries=max_retries
    ).with_structured_output(PlayerReply)
    prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt.format(side=side, convention=convention)),
        ("human", "{turn}"),
    ])

    return prompt | model



