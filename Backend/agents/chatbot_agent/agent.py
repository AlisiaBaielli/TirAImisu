# agent.py
"""
Single-node LangGraph chatbot agent that can:
- read user's current meds
- check pairwise interactions via a DB-backed tool

It uses your logger and the tools defined in tools.py.
"""

from typing import List, Optional
from langgraph.prebuilt import create_react_agent
from langgraph.checkpoint.memory import MemorySaver
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from logger import logger
from tools import TOOLS  # get_current_meds, check_interaction
import dotenv

dotenv.load_dotenv()


SYSTEM_PROMPT = SystemMessage(
    content=(
        "You are a medication assistant. Be concise and safe.\n"
        "- You can look up the user's current medications with the tool `get_current_meds(user_id)`.\n"
        "- You can check if two drugs interact using `check_interaction(drug_a, drug_b)`.\n"
        "- If the user asks about interactions, prefer calling the interaction tool rather than guessing.\n"
        "- If you need the user's id to look up meds and it wasn't provided, ask for it explicitly.\n"
        "- If no interaction is found, clearly say so and recommend consulting a clinician for definitive guidance.\n"
    )
)


class ChatAgent:
    """Minimal single-agent wrapper around a LangGraph ReAct agent."""

    def __init__(self, model: str = "gpt-4o"):
        self.memory = MemorySaver()
        self.llm = ChatOpenAI(model=model)
        # Create a single-node ReAct agent with our tools and system prompt
        self.graph = create_react_agent(
            self.llm,
            tools=TOOLS,
            prompt=SYSTEM_PROMPT,
            checkpointer=self.memory,
        )

    def run(self, text: str, *, thread_id: Optional[str] = None) -> str:
        """
        Synchronous call: send a user message and return the final assistant text.
        """
        logger.log_agent("-> user: " + text)
        events = self.graph.stream(
            {"messages": [HumanMessage(content=text)]},
            config={"thread_id": thread_id or "default"},
        )

        msgs: List = []
        for ev in events:
            # Each event is a dict of node_name -> { "messages": [...] }
            for _, node_out in ev.items():
                for m in node_out.get("messages", []):
                    msgs.append(m)

        ai_msgs = [m for m in msgs if isinstance(m, AIMessage)]
        reply = ai_msgs[-1].content if ai_msgs else "(no response)"
        logger.log_agent_response("Chatbot", reply)
        return reply


# Optional quick REPL for local testing
if __name__ == "__main__":
    agent = ChatAgent()
    print("Meds Chatbot. Type 'quit' to exit.")
    tid = "local-repl"
    while True:
        try:
            q = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if not q or q.lower() in {"quit", "exit"}:
            break
        ans = agent.run(q, thread_id=tid)
        print(f"Bot: {ans}")
