# camera_agent.py
"""
Camera Agent

Flow:
  START
    -> ingest           # image bytes -> multimodal extraction
    -> save             # (stub) persist extracted med
    -> interactions     # (stub) risk assessment
    -> notify           # (stub) notification
       ├─(risk=contraindicated or should_escalate=True)─> escalate_if_red -> END
       └──────────────────────────────────────────────────────────────────> END
"""

from __future__ import annotations
from typing import TypedDict, Dict, Any, List, Optional
import json
import uuid
import base64

from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver
from Backend.agents.logger import logger
from .extract_data_from_img import extract_medication_data_from_image


class CameraState(TypedDict, total=False):
    user_id: str
    image_b64: str
    text: str
    extracted: Dict[str, Any]
    saved: Dict[str, Any]
    interaction: Dict[str, Any]
    notification: Dict[str, Any]
    escalation: Dict[str, Any]
    should_escalate: bool
    activity: List[Dict[str, Any]]


def _log(state: CameraState, stage: str, data: Dict[str, Any]) -> CameraState:
    entry = {"stage": stage, "data": data}
    logger.log_tool_result(stage, entry)
    state.setdefault("activity", []).append(entry)
    return state


class CameraAgent:
    def __init__(self):
        self.memory = MemorySaver()
        self._setup_graph()
        self.something = None  # returned function

    # ───────────────── Nodes ───────────────── #
    def n_ingest(self, state: CameraState) -> CameraState:
        """
        If image_b64 present: decode -> extract medication data (name, dosage, num_pills).
        If text present (fallback): future text parsing (stub).
        """
        extracted: Dict[str, Any] = {}
        if state.get("image_b64"):
            try:
                image_bytes = base64.b64decode(state["image_b64"])
                extracted = extract_medication_data_from_image(image_bytes)
            except Exception as e:
                extracted = {"error": f"extraction_failed: {e}"}
        elif state.get("text"):
            # Placeholder for text parsing path
            extracted = {"note": "text path not implemented"}
        state["extracted"] = extracted
        return _log(state, "ingest", extracted)

    def n_save(self, state: CameraState) -> CameraState:
        """
        Stub: pretend we saved the medication. Would normally write to DB/storage.
        """
        ext = state.get("extracted") or {}
        if ext.get("medication_name"):
            state["saved"] = {
                "saved": True,
                "medication_name": ext.get("medication_name"),
            }
        else:
            state["saved"] = {"saved": False}
        return _log(state, "save", state["saved"])

    def n_interactions(self, state: CameraState) -> CameraState:
        """
        Stub: risk calculation. Always 'none'.
        """
        state["interaction"] = {"overall_risk": "none", "pairs": []}
        return _log(state, "interactions", state["interaction"])

    def n_notify(self, state: CameraState) -> CameraState:
        """
        Stub: notification packaging.
        """
        state["notification"] = {
            "message": "Medication processed",
            "medication_name": (state.get("extracted") or {}).get("medication_name"),
        }
        return _log(state, "notify", state["notification"])

    def n_escalate_if_red(self, state: CameraState) -> CameraState:
        """
        Stub: escalation never triggered unless forced.
        """
        state["escalation"] = {"escalated": True}
        return _log(state, "escalate_if_red", state["escalation"])

    # ───────────────── Graph wiring ───────────────── #
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

        def _branch_after_notify(state: CameraState) -> str:
            inter = state.get("interaction") or {}
            risk = (inter.get("overall_risk") or "none").lower()
            force = bool(state.get("should_escalate", False))
            if force or risk == "contraindicated":
                return "escalate"
            return "finish"

        builder.add_conditional_edges(
            "notify",
            _branch_after_notify,
            {"escalate": "escalate_if_red", "finish": END},
        )
        builder.add_edge("escalate_if_red", END)
        self.graph = builder.compile(checkpointer=self.memory)

    # ───────────────── Runner helper ───────────────── #
    def run(self, message: str, thread_id: Optional[str] = None) -> Dict[str, Any]:
        try:
            data = json.loads(message)
        except Exception:
            data = {"text": message}

        initial: CameraState = {
            "user_id": data.get("user_id", "unknown"),
            "image_b64": data.get("image_b64", ""),
            "text": data.get("text", ""),
            "should_escalate": bool(data.get("should_escalate", False)),
            "activity": [],
        }

        result = self.graph.invoke(
            initial,
            config={"configurable": {"thread_id": thread_id or str(uuid.uuid4())}},
        )

        logger.log_agent_response(
            "CameraAgent",
            f"Completed stages: {', '.join(a['stage'] for a in result.get('activity', []))}",
        )
        return result


if __name__ == "__main__":
    agent = CameraAgent()
    demo = json.dumps(
        {"user_id": "u_demo", "text": "Name=Sertraline; Strength=50 mg; Qty=28"}
    )
    print(agent.run(demo))