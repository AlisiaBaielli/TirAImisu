# camera_agent.py
"""
Camera Agent (skeleton with optional edge)

Flow:
  START
    -> ingest           # photo->text OCR OR direct text parse
    -> save             # persist extracted med + stock
    -> interactions     # check interactions vs current meds
    -> notify           # send user notification
       ├─(risk=contraindicated or should_escalate=True)─> escalate_if_red  -> END
       └───────────────────────────────────────────────────────────────────> END

All node implementations are intentionally empty/stubbed. Fill in later.
"""

from __future__ import annotations
from typing import TypedDict, Dict, Any, List, Optional
import json
import uuid

from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver
from Backend.agents.chatbot_agent.logger import (
    logger,
)  # expects your existing logger with .log_tool_result / .log_agent_response


# ──────────────────────────── Pipeline State ────────────────────────────
class CameraState(TypedDict, total=False):
    # Inputs
    user_id: str
    image_b64: str
    text: str

    # Artifacts by stage (populate later when you add logic)
    extracted: Dict[str, Any]
    saved: Dict[str, Any]
    interaction: Dict[
        str, Any
    ]  # expected to contain "overall_risk": "none"|"caution"|"contraindicated"
    notification: Dict[str, Any]
    escalation: Dict[str, Any]

    # Optional override to force escalation path
    should_escalate: bool

    # Running log for UI
    activity: List[Dict[str, Any]]


def _log(state: CameraState, stage: str, data: Dict[str, Any]) -> CameraState:
    """Append a structured activity entry (mirrors your previous pipeline)."""
    entry = {"stage": stage, "data": data}
    logger.log_tool_result(stage, entry)
    state.setdefault("activity", []).append(entry)
    return state


# ────────────────────────────── Agent Class ─────────────────────────────
class CameraAgent:
    """Node-based pipeline with empty node implementations."""

    def __init__(self):
        self.memory = MemorySaver()
        self._setup_graph()

    # ───────────── Nodes (EMPTY implementations; add logic later) ───────────── #
    def n_ingest(self, state: CameraState) -> CameraState:
        """
        TODO:
        - If image_b64 present: OCR to extract {name, strength, sig, quantity, times[]}
        - Else if text present: parse into the same structure
        - Put results into state["extracted"]
        """
        return _log(state, "ingest", {"note": "stub; no extraction performed"})

    def n_save(self, state: CameraState) -> CameraState:
        """
        TODO:
        - Persist medication + stock to your DB
        - Return identifiers/flags in state["saved"]
        """
        return _log(state, "save", {"note": "stub; nothing saved"})

    def n_interactions(self, state: CameraState) -> CameraState:
        """
        TODO:
        - Compare new med vs user's current meds from DB
        - Compute overall_risk and pairwise details
        - Put results into state["interaction"], e.g. {"overall_risk": "none", "pairs": [...]}
        """
        return _log(state, "interactions", {"note": "stub; no checks performed"})

    def n_notify(self, state: CameraState) -> CameraState:
        """
        TODO:
        - Send a notification to the user summarizing the addition + risk
        - Place provider response into state["notification"]
        """
        return _log(state, "notify", {"note": "stub; no notifications sent"})

    def n_escalate_if_red(self, state: CameraState) -> CameraState:
        """
        TODO:
        - Request permission to email doctor
        - If granted, send email with details
        - Save results into state["escalation"]
        """
        return _log(state, "escalate_if_red", {"note": "stub; no escalation"})

    # ─────────────────────────── Graph wiring ─────────────────────────── #
    def _setup_graph(self):
        builder = StateGraph(CameraState)

        builder.add_node("ingest", self.n_ingest)
        builder.add_node("save", self.n_save)
        builder.add_node("interactions", self.n_interactions)
        builder.add_node("notify", self.n_notify)
        builder.add_node("escalate_if_red", self.n_escalate_if_red)

        builder.add_edge(START, "ingest")
        builder.add_edge("ingest", "save")
        builder.add_edge("save", "interactions")
        builder.add_edge("interactions", "notify")

        # ---- Optional edge branching after notify ----
        def _branch_after_notify(state: CameraState) -> str:
            """
            Decide whether to escalate or finish.
            Implementations should set state["interaction"]["overall_risk"].
            You can also force escalation by setting state["should_escalate"] = True.
            """
            inter = state.get("interaction") or {}
            risk = (inter.get("overall_risk") or "none").lower()
            force = bool(state.get("should_escalate", False))
            if force or risk == "contraindicated":
                return "escalate"
            return "finish"

        builder.add_conditional_edges(
            "notify",
            _branch_after_notify,
            {
                "escalate": "escalate_if_red",
                "finish": END,
            },
        )

        builder.add_edge("escalate_if_red", END)

        self.graph = builder.compile(checkpointer=self.memory)

    # ─────────────────────────── Runner API ─────────────────────────── #
    def run(self, message: str, thread_id: Optional[str] = None) -> str:
        """
        Accepts JSON string:
          {"user_id":"u_demo","image_b64":"..."}  OR
          {"user_id":"u_demo","text":"Name=..., Strength=..., Dose=..., Qty=..., Times=..."}
        Returns a compact summary (stubbed) and logs activity.
        """
        try:
            data = json.loads(message)
            user_id = data.get("user_id") or "unknown"
            image_b64 = data.get("image_b64") or ""
            text = data.get("text") or ""
            should_escalate = bool(data.get("should_escalate", False))
        except Exception:
            user_id, image_b64, text, should_escalate = "unknown", "", message, False

        initial: CameraState = {
            "user_id": user_id,
            "image_b64": image_b64,
            "text": text,
            "should_escalate": should_escalate,
            "activity": [],
        }

        result = self.graph.invoke(
            initial,
            config={"configurable": {"thread_id": thread_id or str(uuid.uuid4())}},
        )

        summary = (
            f"Ingest complete for user={user_id}. "
            f"Stages run: {', '.join(a['stage'] for a in result.get('activity', []))}."
        )
        logger.log_agent_response("CameraAgent", summary)
        return summary


# Optional local smoke test (kept minimal)
if __name__ == "__main__":
    agent = CameraAgent()
    demo = json.dumps(
        {
            "user_id": "u_demo",
            "text": "Name=Sertraline; Strength=50 mg; Dose=once daily; Qty=28; Times=08:00",
            "should_escalate": False,
        }
    )
    print(agent.run(demo))
