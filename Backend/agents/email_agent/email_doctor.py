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

    key = os.getenv("OPENAI_API_KEY")
    if not key:
        raise RuntimeError(
            "No API key provided. Set OPENAI_API_KEY in the environment or copy .env.example to .env and set your key there."
        )

    base = os.getenv("OPENAI_BASE_URL")
    client = openai.OpenAI(api_key=key, base_url=base)

    model = "gpt-5-nano"
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


def send_email_to_doctor(user_id: int, content: str) -> Dict[str, Any]:
    """
    1. Loads user (and doctor) info from personal_data.json
    2. Generates email text
    3. Sends via Resend API (RESEND_API_KEY required)
    Returns dict with success / message_id / to / from / subject or error.
    """
    data_path = Path(__file__).resolve().parent.parent.parent / "data" / "personal_data.json"
    try:
        with open(data_path, "r") as f:
            users = json.load(f)
    except FileNotFoundError:
        return {"success": False, "error": f"personal_data.json not found at {data_path}"}
    except json.JSONDecodeError as e:
        return {"success": False, "error": f"Invalid JSON in personal_data.json: {e}"}

    user = next((u for u in users if str(u.get("user_id")) == str(user_id)), None)
    if not user:
        return {"success": False, "error": f"User with user_id={user_id} not found"}
    
    # Find the user
    user_email = user.get("email")
    doctor_email = user.get("doctor_email")
    user_name = user.get("full_name") or "Patient"

    if not user_email or not doctor_email:
        return {"success": False, "error": "Missing user email or doctor_email"}

    # Generate email body
    try:
        email_data = generate_doctor_email(content)
        subject = email_data.get("subject") or "Drug Interaction Inquiry"
        body = email_data.get("email") or ""
        # Append signature if not already
        if user_name.lower() not in body.lower():
            body += f"\n\nBest regards,\n{user_name}"
    except Exception as e:
        return {"success": False, "error": f"Failed to generate email: {e}"}

    api_key = os.getenv("RESEND_API_KEY", "").strip()
    if not api_key:
        return {"success": False, "error": "RESEND_API_KEY not set"}

    url = "https://api.resend.com/emails"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    # Dynamic (non-hardcoded) doctor + reply_to
    payload = {
        "from": f"{user_name} <onboarding@resend.dev>",
        "to": [doctor_email],
        "reply_to": user_email,
        "subject": subject,
        "text": body,
    }
    
    try:
        r = requests.post(url, headers=headers, json=payload, timeout=15)
        r.raise_for_status()
        resp_json = r.json()
        return {
            "success": True,
            "message_id": resp_json.get("id"),
            "to": [doctor_email],
            "from": user_email,
            "subject": subject,
        }
    except requests.exceptions.RequestException as e:
        detail = ""
        if getattr(e, "response", None) is not None:
            try:
                detail = f" - {e.response.json()}"
            except Exception:
                detail = f" - {e.response.text}"
        return {"success": False, "error": f"Failed to send email: {e}{detail}"}


if __name__ == "__main__":
    demo = "Potential interaction between Lisinopril and Ibuprofen. Please advise."
    print(send_email_to_doctor(user_id=1, content=demo))
