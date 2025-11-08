import os
import requests
import openai
import json
from typing import Optional, List, Tuple, Dict, Any 
from pydantic import BaseModel, Field
from dotenv import load_dotenv  

# Pydantic Model 
class InteractionReport(BaseModel):
    interaction_found: bool = Field(..., description="Set to true if an interaction is found, false otherwise.")
    severity: Optional[str] = Field(None, description="The severity of the interaction (e.g., 'Mild', 'Moderate', 'Severe') if found.")
    description: Optional[str] = Field(None, description="A concise, one-sentence summary of the interaction if found.")
    extended_description: Optional[str] = Field(None, description="A detailed explanation of the interaction's mechanism, effects, and management if found.")

load_dotenv() 

try:
    # Check if the key was loaded successfully
    if not os.environ.get("OPENAI_API_KEY"):
        raise openai.OpenAIError("OPENAI_API_KEY not found. Make sure it's set in your .env file.")
    
    # The client will now automatically find the key
    client = openai.OpenAI(
            api_key="sk-r0hwmHPWW8yghQ0_axmBfw",
        base_url="https://fj7qg3jbr3.execute-api.eu-west-1.amazonaws.com/v1"
    )
    
except openai.OpenAIError as e:
    print(f"Error initializing OpenAI client: {e}")
    exit()

def get_interaction_text(drug_name: str) -> str | None:
    """
    Fetches the 'drug_interactions' section from openFDA for a given drug.
    If not found, it falls back to the 'warnings' section.
    """
    print(f"🔄 Caching label for '{drug_name}'...")
    url = "https://api.fda.gov/drug/label.json"
    search_term = drug_name.upper()
    params = {'search': f'openfda.generic_name:"{search_term}"', 'limit': 1}

    prepared_request = requests.Request('GET', url, params=params).prepare()
    # print(f"🔍 Full API query URL: {prepared_request.url}") # Uncomment for debugging

    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        data = response.json()

        if 'results' in data and len(data['results']) > 0:
            result = data['results'][0]
            # print(f"👀 JSON Preview (Top-level keys): {list(result.keys())}") # Uncomment for debugging

            if 'drug_interactions' in result:
                # print("✅ Found dedicated 'drug_interactions' field.") # Uncomment for debugging
                return " ".join(result['drug_interactions'])
            elif 'warnings' in result:
                # print("⚠️ No 'drug_interactions' field found. Falling back to 'warnings' section.") # Uncomment for debugging
                return " ".join(result['warnings'])
            else:
                print(f"❌ No 'drug_interactions' OR 'warnings' field found for '{drug_name}'.")
                return None
        else:
            print(f"❌ No drug label found for '{drug_name}'.")
            return None
    except requests.RequestException as e:
        if e.response and e.response.status_code == 404:
             print(f"❌ No drug label found for '{drug_name}' (404 Error).")
        else:
             print(f"HTTP Error: {e}")
        return None
    
def _get_drug_label(drug_name: str) -> Optional[Dict[str, Any]]:
    """
    Internal helper to fetch the full openFDA label for a drug.
    """
    print(f"🔄 Fetching full label for '{drug_name}'...")
    url = "https://api.fda.gov/drug/label.json"
    search_term = drug_name.upper()
    params = {'search': f'openfda.generic_name:"{search_term}"', 'limit': 1}

    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        data = response.json()

        if 'results' in data and len(data['results']) > 0:
            return data['results'][0] # Return the entire first result
        else:
            print(f"❌ No drug label found for '{drug_name}'.")
            return None
    except requests.RequestException as e:
        if e.response and e.response.status_code == 404:
             print(f"❌ No drug label found for '{drug_name}' (404 Error).")
        else:
             print(f"HTTP Error: {e}")
        return None

def check_interaction_with_llm(interaction_text: str, drug_a_name: str, drug_b_name: str) -> Optional[InteractionReport]:
    """
    Asks an LLM to analyze the interaction text and return a structured report.
    """
    print(f"🧠 Analyzing {drug_a_name}'s label for '{drug_b_name}'...")

    system_prompt = (
        "You are an expert pharmacologist. You will be given text from a drug label and the name of a second drug. "
        "Your task is to analyze the text and determine if an interaction with the second drug (or its class) is described. "
        "You must respond using the `report_interaction` tool. If no interaction is found, set `interaction_found` to false."
    )
    user_prompt = (
        f"Drug Label Text (for {drug_a_name}):\n"
        f"---START TEXT---\n{interaction_text}\n---END TEXT---\n\n"
        f"Analyze this text for any interactions with the drug '{drug_b_name}'."
    )
    tools = [
        {
            "type": "function",
            "function": {
                "name": "report_interaction",
                "description": "Report the findings of the drug interaction analysis.",
                "parameters": InteractionReport.model_json_schema()
            }
        }
    ]
    try:
        response = client.chat.completions.create(
            model="gpt-5-nano",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            tools=tools,
            tool_choice={"type": "function", "function": {"name": "report_interaction"}}
        )
        message = response.choices[0].message
        if message.tool_calls:
            tool_call = message.tool_calls[0]
            function_args = json.loads(tool_call.function.arguments)
            report = InteractionReport(**function_args)
            return report
        else:
            print("🤖 LLM did not call the tool as expected.")
            return None
    except openai.OpenAIError as e:
        print(f"Error calling OpenAI API: {e}")
        return None
    except json.JSONDecodeError as e:
        print(f"Error parsing LLM response: {e}")
        return None

def synthesize_reports(reports: List[InteractionReport], drug_a: str, drug_b: str) -> Optional[InteractionReport]:
    """
    Takes a list of found interaction reports and synthesizes them into a single,
    definitive report.
    """
    if not reports:
        return None
    if len(reports) == 1:
        return reports[0]

    print(f"\n🧠 Synthesizing {len(reports)} reports for {drug_a} <-> {drug_b}...")
    system_prompt = (
        "You are an expert clinical pharmacologist. You will be given one or more "
        "drug interaction reports. Your task is to synthesize them "
        "into a single, comprehensive, and definitive report.\n"
        "Rules:\n"
        "1. **Prioritize Severity:** The final report MUST use the **most severe** one found.\n"
        "2. **Combine Descriptions:** Synthesize the descriptions into the most complete and clear explanation.\n"
        "3. **Respond with Tool:** You must respond using the `report_interaction` tool."
    )
    report_texts = []
    for i, report in enumerate(reports, 1):
        report_texts.append(
            f"---Source Report {i}---\n"
            f"Severity: {report.severity}\n"
            f"Description: {report.description}\n"
            f"Extended Description: {report.extended_description}\n"
        )
    user_prompt = (
        f"Please synthesize the following reports about an interaction "
        f"between '{drug_a}' and '{drug_b}' into one, final report.\n\n"
        + "\n".join(report_texts)
    )
    tools = [
        {
            "type": "function",
            "function": {
                "name": "report_interaction",
                "description": "Report the final, synthesized interaction findings.",
                "parameters": InteractionReport.model_json_schema()
            }
        }
    ]
    try:
        response = client.chat.completions.create(
            model="gpt-5-nano",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            tools=tools,
            tool_choice={"type": "function", "function": {"name": "report_interaction"}}
        )
        message = response.choices[0].message
        if message.tool_calls:
            tool_call = message.tool_calls[0]
            function_args = json.loads(tool_call.function.arguments)
            final_report = InteractionReport(**function_args)
            final_report.interaction_found = True
            return final_report
        else:
            print("🤖 LLM did not call the synthesis tool as expected.")
            return None
    except openai.OpenAIError as e:
        print(f"Error calling OpenAI API during synthesis: {e}")
        return None
    except json.JSONDecodeError as e:
        print(f"Error parsing LLM synthesis response: {e}")
        return None

# --- *** NEW REFACTORED MAIN FUNCTION *** ---
#
# This is the function you will import from other files.
#
def check_new_medication_against_list(existing_drug_list: List[str], new_drug: str) -> List[Tuple[str, str, InteractionReport]]:
    """
    Checks a new medication against a list of existing medications for interactions.

    Args:
        existing_drug_list: A list of drug names (e.g., ["Warfarin", "Lisinopril"])
        new_drug: The single new drug name to check (e.g., "Ibuprofen")

    Returns:
        A list of tuples, where each tuple contains:
        (new_drug_name, existing_drug_name, InteractionReport_object)
        Returns an empty list if no interactions are found.
    """
    
    print(f"\nChecking '{new_drug}' against {len(existing_drug_list)} existing medications: {', '.join(existing_drug_list)}")

    # 1. Cache Phase: Fetch n+1 labels
    print("\n--- Phase 1: Fetching and Caching Labels ---")
    drug_label_cache = {}
    
    # Cache the new drug's label
    drug_label_cache[new_drug] = get_interaction_text(new_drug)
    
    # Cache all existing drugs' labels
    for drug in existing_drug_list:
        if drug.upper() != new_drug.upper():
            drug_label_cache[drug] = get_interaction_text(drug)
            
    print("--- Cache phase complete. ---")

    
    # 2. Analysis Phase (New Drug vs. Each Existing Drug)
    print("\n--- Phase 2: Analyzing Interactions ---")
    all_final_reports = [] # Store final (drug_a, drug_b, report) tuples
    
    text_new_drug = drug_label_cache.get(new_drug)

    for existing_drug in existing_drug_list:
        
        if new_drug.upper() == existing_drug.upper():
            continue
            
        print(f"\n--- Checking Pair: {new_drug} <-> {existing_drug} ---")
        
        reports_for_this_pair = []
        text_existing_drug = drug_label_cache.get(existing_drug)
        
        # Check 1: New Drug's label for Existing Drug
        if text_new_drug:
            report_a = check_interaction_with_llm(text_new_drug, new_drug, existing_drug)
            if report_a and report_a.interaction_found:
                reports_for_this_pair.append(report_a)
        
        # Check 2: Existing Drug's label for New Drug
        if text_existing_drug:
            report_b = check_interaction_with_llm(text_existing_drug, existing_drug, new_drug)
            if report_b and report_b.interaction_found:
                if not any(r.description == report_b.description for r in reports_for_this_pair):
                    reports_for_this_pair.append(report_b)

        # Synthesize the findings for this one pair
        if reports_for_this_pair:
            final_pair_report = synthesize_reports(reports_for_this_pair, new_drug, existing_drug)
            if final_pair_report:
                all_final_reports.append((new_drug, existing_drug, final_pair_report))
        else:
            print(f"✅ No interaction found for {new_drug} <-> {existing_drug}")

    # 3. Return the results
    return all_final_reports

def get_drug_side_effects(drug_name: str) -> str:
    """
    Returns the side effects and warnings for a single drug
    by searching the FDA's official drug labels.

    Args:
        drug_name: The name of the drug to search for.

    Returns:
        A string containing the side effect/warning information, or
        a message if no information is found.
    """
    print(f"Tool 'get_drug_side_effects' called for: {drug_name}")
    
    label_data = _get_drug_label(drug_name)
    
    if not label_data:
        result = f"No drug label could be found for '{drug_name}'."
        print(f"Tool 'get_drug_side_effects' result: {result}")
        return result

    # Check for fields in order of preference
    # 1. 'adverse_reactions': Most specific to side effects
    # 2. 'warnings_and_cautions': A common field
    # 3. 'warnings': A general fallback
    
    text_to_return = None
    
    if 'adverse_reactions' in label_data:
        text_to_return = " ".join(label_data['adverse_reactions'])
    elif 'warnings_and_cautions' in label_data:
        text_to_return = " ".join(label_data['warnings_and_cautions'])
    elif 'warnings' in label_data:
        text_to_return = " ".join(label_data['warnings'])

    if text_to_return:
        # Provide context on where the info came from
        result_header = f"Found the following information for {drug_name} (this is not a complete list):\n\n"
        result = result_header + text_to_return
    else:
        result = f"A label was found for '{drug_name}', but it did not contain a specific 'adverse_reactions' or 'warnings' section."
        
    print(f"Tool 'get_drug_side_effects' result: Found {len(result)} chars")
    
    # Return a single string, as required by LLM tools
    return result

# --- *** NEW TEST BLOCK *** ---
#
# This code ONLY runs when you execute `python drug_interactions.py` directly
# It WILL NOT run when you import this file from elsewhere.
#
if __name__ == "__main__":
    print("--- Running drug_interactions.py as a standalone script for testing ---")
    
    # 1. Set up the test data
    test_existing_list = ["Warfarin", "Lisinopril", "Simvastatin", "Ibuprofen"]
    print(f"💊 Existing Medications (hard-coded): {', '.join(test_existing_list)}")
    
    test_new_drug = input("Enter the NEW medication to check:\n(e.g., Aspirin or Clarithromycin)\n> ").strip()

    if test_new_drug:
        # 2. Call the main function
        interaction_results = check_new_medication_against_list(test_existing_list, test_new_drug)
        
        # 3. Print the results (this is the logic from your old 'main')
        print(f"\n--- 🏁 Final Interaction Report for '{test_new_drug}' ---")
        if interaction_results:
            print(f"🚨 Found {len(interaction_results)} potential interaction(s) between '{test_new_drug}' and the existing medication list.")
            
            for i, (drug_a, drug_b, report) in enumerate(interaction_results, 1):
                print("\n-------------------------------------------")
                print(f"  Interaction {i}: {drug_a} and {drug_b}")
                print(f"  Severity: {report.severity}")
                print(f"  Description: {report.description}")
                print(f"  Extended Description: {report.extended_description}")
            
            print("\nNote: Please consult a healthcare professional for medical advice.")
        else:
            print(f"✅ No specific interactions were found between '{test_new_drug}' and the existing medications.")
            print("Note: This is not a substitute for professional medical advice.")
    else:
        print("No new drug entered. Exiting test.")