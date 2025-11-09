"""Helpers to generate professional emails to a doctor using a GPT-5 agent.

Primary function: generate_doctor_email(to_email: str, content: str) -> str

This will create an OpenAI client using the pattern requested by the user and
call the chat completions endpoint with temperature=1.
"""
from __future__ import annotations

from typing import Optional, Dict, Any
import os
import openai
import json
from pydantic import BaseModel
import requests
from pathlib import Path


def generate_doctor_email(content: str) -> str:
    """Generate a professional email to a doctor about a potential drug interaction.

    Parameters
    - to_email: recipient doctor's email address (used only in the prompt; function does not send email)
    - content: additional context to include in the prompt (e.g., the two drugs, patient details, symptoms)

    Returns a dict: {"subject": str, "email": str}
    """

    key = os.getenv("OPENAI_API_KEY") or "sk-r0hwmHPWW8yghQ0_axmBfw"
    if not key:
        raise RuntimeError(
            "No API key provided. Set OPENAI_API_KEY in the environment or copy .env.example to .env and set your key there."
        )

    base = os.getenv("OPENAI_BASE_URL") or "https://fj7qg3jbr3.execute-api.eu-west-1.amazonaws.com/v1"
    client = openai.OpenAI(api_key=key, base_url=base)

    model = "gpt-5"
    system_msg = {
        "role": "system",
        "content": "Generate a professional medical email in JSON format. Be concise and formal.",
    }

    user_prompt = (
        f"Generate a brief professional email to a doctor asking about the safety of a drug interaction."
        f"Start with 'Dear Doctor'. Context (no verbatim please): {content}\n\n"
        f"Return JSON with keys 'subject' (short) and 'email' (greeting + 2-3 sentences + closing). "
        "Use formal tone. No contact details. Do not include a signature."
    )

    user_msg = {"role": "user", "content": user_prompt}

    messages = [system_msg, user_msg]

    try:
        resp = client.chat.completions.create(model=model, messages=messages, temperature=1)
    except Exception as e:
        raise RuntimeError(f"Error calling chat completions API: {e}")

    try:
        model_text = resp.choices[0].message.content.strip()
    except Exception:
        # Fallback: try dict-style access
        try:
            model_text = resp["choices"][0]["message"]["content"].strip()
        except Exception as e:
            raise RuntimeError(f"Unexpected response shape from model: {e}")

    # Helper: extract first balanced JSON object from model_text
    def _extract_json_from_text(text: str) -> Dict[str, Any]:
        idx = text.find("{")
        if idx == -1:
            raise ValueError("No JSON object found in model response")
        jtxt = text[idx:]
        stack = []
        end = None
        for i, ch in enumerate(jtxt):
            if ch == '{':
                stack.append('{')
            elif ch == '}':
                if stack:
                    stack.pop()
                    if not stack:
                        end = i + 1
                        break
        if end is None:
            raise ValueError("Could not find balanced JSON object in model response")
        jsubstr = jtxt[:end]
        try:
            return json.loads(jsubstr)
        except Exception:
            cleaned = jsubstr.strip().strip('`')
            return json.loads(cleaned)

    parsed = None
    try:
        parsed = _extract_json_from_text(model_text)
    except Exception:
        # Retry once asking the model to output strict JSON only
        retry_prompt = (
            "Please respond ONLY with a single JSON object with the keys: subject, email. "
            "Do not include any additional text. If unknown, set value to null.\n\nOriginal response:\n" + model_text
        )
        retry_messages = [
            system_msg,
            {"role": "user", "content": retry_prompt},
        ]
        resp2 = client.chat.completions.create(model=model, messages=retry_messages, temperature=1)
        try:
            model_text2 = resp2.choices[0].message.content.strip()
        except Exception:
            model_text2 = resp2["choices"][0]["message"]["content"].strip()
        parsed = _extract_json_from_text(model_text2)

    class GeneratedEmail(BaseModel):
        subject: Optional[str]
        email: Optional[str]

    gen = GeneratedEmail(**(parsed or {}))
    return {"subject": gen.subject, "email": gen.email}


def send_email_to_doctor(user_id: int, content: str) -> Dict[str]:
    """Send an email to the doctor using Resend API.
    
    This function:
    1. Loads user data from personal_data.json based on user_id
    2. Generates email content using generate_doctor_email()
    3. Sends the email using Resend API
    
    Parameters:
        user_id: The user ID to look up in personal_data.json (default: 1)
        content: The drug interaction information to include in the email
    
    Returns:
        Dict with 'success' (bool), 'message_id' (str if successful), 'error' (str if failed)
    
    Environment Variables Required:
        RESEND_API_KEY: Your Resend API key
    """
    # Load personal data
    data_path = Path(__file__).parent.parent.parent / "data" / "personal_data.json"
    
    try:
        with open(data_path, 'r') as f:
            users = json.load(f)
    except FileNotFoundError:
        return {"success": False, "error": f"personal_data.json not found at {data_path}"}
    except json.JSONDecodeError as e:
        return {"success": False, "error": f"Invalid JSON in personal_data.json: {e}"}
    
    # Find the user
    user = None
    for u in users:
        if str(u.get("user_id")) == str(user_id):
            user = u
            break
    
    if not user:
        return {"success": False, "error": f"User with user_id={user_id} not found"}
    
    user_email = user.get("email")
    doctor_email = user.get("doctor_email")
    user_name = user.get("full_name")
    
    if not user_email or not doctor_email:
        return {"success": False, "error": "Missing email or doctor_email in user data"}
    
    # Generate email content
    try:
        email_data = generate_doctor_email(content)
        subject = email_data.get("subject", "Drug Interaction Inquiry")
        email_body = email_data.get("email", "")
        
        # Add signature
        if user_name and user_name.lower() not in email_body.lower():
            email_body += f"\n\nBest regards,\n{user_name}"
            
    except Exception as e:
        return {"success": False, "error": f"Failed to generate email: {e}"}
    
    # Send email using Resend API
    api_key = os.getenv("RESEND_API_KEY") or "re_cuZbaUn5_H8iRKUnzXVeAPPafmxjEQq5z"
    if not api_key:
        return {"success": False, "error": "RESEND_API_KEY not set in environment"}
    
    url = "https://api.resend.com/emails"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "from": f"{user_name} <onboarding@resend.dev>",  # Resend's default sender for testing
        #"to": [doctor_email],
        "to": ["devpereira1@gmail.com"],
        #"reply_to": user_email,
        "reply_to": "devpereira1@gmail.com",
        "subject": subject,
        "text": email_body,
    }
    
    try:
        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()
        result = response.json()
        return {
            "success": True,
            "message_id": result.get("id"),
            #"to": doctor_email,
            "to": ["devpereira1@gmail.com"],
            "from": user_email,
            "subject": subject
        }
    except requests.exceptions.RequestException as e:
        error_msg = str(e)
        if hasattr(e, 'response') and e.response is not None:
            try:
                error_detail = e.response.json()
                error_msg = f"{error_msg} - {error_detail}"
            except Exception:
                error_msg = f"{error_msg} - {e.response.text}"
        return {"success": False, "error": f"Failed to send email: {error_msg}"}


if __name__ == "__main__":
    sample = '''Zyrtec and Xanax are conflicting because they may cause excessive drowsiness. From Devin Pereira''' 
    result = send_email_to_doctor(user_id=1, content=sample)
    print(result)
