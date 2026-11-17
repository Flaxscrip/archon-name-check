"""python -m name_check [port]   (PUBLIC_URL names the address on the agent card; HOST defaults to 127.0.0.1)"""
import os
import sys

import uvicorn
from a2a.server.apps import A2AStarletteApplication
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.tasks import InMemoryTaskStore

from .agent import NameCheckExecutor, create_agent_card
from .demo import demo, landing

PORT = int(sys.argv[1]) if len(sys.argv) > 1 else int(os.environ.get("PORT", 8090))

app = A2AStarletteApplication(
    agent_card=create_agent_card(os.environ.get("PUBLIC_URL", f"http://localhost:{PORT}")),
    http_handler=DefaultRequestHandler(agent_executor=NameCheckExecutor(), task_store=InMemoryTaskStore()),
).build()
# Two pages for people, beside the agent's own routes (POST / and the card).
app.add_route("/", landing, methods=["GET"])
app.add_route("/demo", demo, methods=["GET"])

if __name__ == "__main__":
    uvicorn.run(app, host=os.environ.get("HOST", "127.0.0.1"), port=PORT)
