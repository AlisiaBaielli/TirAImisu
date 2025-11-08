# tools.py
"""
LangChain tools for the medication chatbot.
Backed by the fake DB layer (db.py) so we can later swap in real persistence.
Includes logging via logger.py.
"""

from typing import List, Dict, Any
from langchain_core.tools import tool

# from Backend.calendar.cal_api import list_events
from Backend.data.utils import retrieve_medications
from Backend.drug_interactions.drug_interactions import get_interaction_text

# from db import db_get_user_meds, db_check_pair_interaction
from Backend.agents.logger import logger  # ✅ import your custom logger


@tool
def get_user_id() -> List[Dict[str, Any]]:
    """
    Return the user id for the current user.
    """
    logger.log_tool_call("get_user_id", {})

    # meds = db_get_user_meds(user_id)
    id = "1"

    logger.log_tool_result("get_user_id", id)
    return id


@tool
def get_current_meds(user_id: str) -> List[Dict[str, Any]]:
    """
    Return the list of medications a user is currently taking.
    Each medication has: {name, strength, sig}.
    """
    logger.log_tool_call("get_current_meds", {"user_id": user_id})
    meds = retrieve_medications(user_id)
    logger.log_tool_result("get_current_meds", meds)
    return meds


@tool
def check_side_effects(drug: str) -> Dict[str, Any]:
    """
    get the interaction information for a given drug from database
    """
    logger.log_tool_call("check_side_effects", {"drug": drug})

    result = get_interaction_text(drug)

    logger.log_tool_result("check_side_effects", result)
    return result


# @tool
# def check_interaction(drug1: str) -> Dict[str, Any]:
#     """
#     get the interaction information for a given drug from database
#     """
#     logger.log_tool_call("check_side_effects", {"drug": drug})

#     result = get_interaction_text(drug)

#     logger.log_tool_result("check_side_effects", result)
#     return result


# @tool  # ALREADY EXISTS
# def get_calendar_events() -> Dict[str, Any]:
#     """Get calendar events for the user. Here you can check if any of the events are related to drinking or driving
#     based on that and the medications they have taken you can provide advice to the user.
#     """

#     return list_events()


# Export list for create_react_agent()
TOOLS = [get_user_id, get_current_meds, check_side_effects]
