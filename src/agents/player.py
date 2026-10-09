from langchain.agents import create_agent
from langchain.chat_models import init_chat_model
from langgraph.graph.state import CompiledStateGraph

from models.bidding.call import PlayerReply
from consts import SEAT_NAMES, CONVENTION

system_prompt = """
You are a bridge player on {side} side. Your task is to take part in a bidding stage of a game.
You receive auction history and Your previous thoughts. You have to decide what to bid on your turn.
Use {convention} bidding convention.
"""

def create_player(
    model_name: str,
    side: SEAT_NAMES,
    convention: CONVENTION
) -> CompiledStateGraph:

    model = init_chat_model(model_name)

    player_agent = create_agent(
        model,
        system_prompt = system_prompt.format(side=side, convention=convention),
        response_format = PlayerReply
    )

    return player_agent
    



