# tools.py
"""
LangChain tools for the medication chatbot.
Backed by the fake DB layer (db.py) so we can later swap in real persistence.
Includes logging via logger.py.
"""

from typing import List, Dict, Any
from langchain_core.tools import tool

# from db import db_get_user_meds, db_check_pair_interaction
from logger import logger  # ✅ import your custom logger


@tool
def get_current_meds(user_id: str) -> List[Dict[str, Any]]:
    """
    Return the list of medications a user is currently taking.
    Each medication has: {name, strength, sig}.
    """
    logger.log_tool_call("get_current_meds", {"user_id": user_id})

    # meds = db_get_user_meds(user_id)

    logger.log_tool_result("get_current_meds", meds)
    return meds


@tool
def check_interaction(drug_a: str, drug_b: str) -> Dict[str, Any]:
    """
    Check whether two medications interact.
    Returns structure:
        {
            "risk": "none" | "caution" | "contraindicated",
            "mechanism": "...",
            "recommendation": "...",
            "sources": [...]
        }
    If no interaction exists, 'risk' will be "none".
    """
    logger.log_tool_call("check_interaction", {"drug_a": drug_a, "drug_b": drug_b})

    # result = db_check_pair_interaction(drug_a, drug_b)

    if result is None:
        result = {
            "risk": "none",
            "mechanism": "No known interaction in database.",
            "recommendation": "Standard use.",
            "sources": [],
        }

    logger.log_tool_result("check_interaction", result)
    return result


# Export list for create_react_agent()
TOOLS = [get_current_meds, check_interaction]
