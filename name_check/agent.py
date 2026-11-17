"""An A2A agent with one skill: who is <name>@archon.social?"""
from __future__ import annotations

from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.events import EventQueue
from a2a.server.tasks import TaskUpdater
from a2a.types import AgentCapabilities, AgentCard, AgentSkill, DataPart, Part, TextPart

from .lookup import DOMAINS, describe, find_name, who_is

VERSION = "0.1.0"
EXAMPLE = f"Who is genitrix@{DOMAINS[0]}?"


def create_agent_card(public_url: str) -> AgentCard:
    return AgentCard(
        name="Archon name check",
        description=(
            "Looks up a name on an Archon name service and tells you which decentralised identifier (DID) is behind it, "
            "whether that DID resolves on an independent resolver, and whether a Lightning address answers for it. "
            "It reads public data only and holds no keys; every answer comes with the URL to check it yourself."
        ),
        url=public_url.rstrip("/") + "/",
        version=VERSION,
        default_input_modes=["text"],
        default_output_modes=["text"],
        capabilities=AgentCapabilities(streaming=False),
        skills=[
            AgentSkill(
                id="who-is",
                name="Say who is behind a name",
                description=(
                    f"Give me a name such as genitrix@{DOMAINS[0]}. I answer with its DID, the keys and services its DID "
                    "document publishes, and its Lightning address, each with a link you can verify without me. "
                    f"I only know names on: {', '.join(DOMAINS)}."
                ),
                tags=["identity", "did", "did:cid", "archon", "lightning"],
                examples=[EXAMPLE, f"Where do I pay genitrix@{DOMAINS[0]}?"],
            )
        ],
    )


class NameCheckExecutor(AgentExecutor):
    async def execute(self, context: RequestContext, event_queue: EventQueue) -> None:
        updater = TaskUpdater(event_queue, context.task_id, context.context_id)
        found = find_name(context.get_user_input())
        if not found:
            # Not a failure: the caller has not said who they mean yet. The task stays open for the answer.
            ask = f"Which name? Give me one like genitrix@{DOMAINS[0]}. I only know names on: {', '.join(DOMAINS)}."
            await updater.requires_input(updater.new_agent_message([Part(root=TextPart(kind="text", text=ask))]), final=True)
            return
        result = await who_is(*found)
        # The same answer twice: as text to read, and as data for a caller that wants to act on it.
        await updater.add_artifact([Part(root=DataPart(kind="data", data=result))], name="who-is")
        await updater.complete(updater.new_agent_message([Part(root=TextPart(kind="text", text=describe(result)))]))

    async def cancel(self, context: RequestContext, event_queue: EventQueue) -> None:
        raise Exception("cancel not supported")
