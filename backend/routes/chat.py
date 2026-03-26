from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from pydantic import BaseModel
from database import get_db
from models import Doctor, Appointment, AvailabilityRule
from openai import OpenAI
from datetime import datetime
import os
import json
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), '..', '..', '.env'))

router = APIRouter(prefix="/api", tags=["chat"])
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

SYSTEM_PROMPT = """You are a helpful assistant for a medical clinic in Bulgaria.
You help patients with:
1. Booking appointments
2. Checking appointments by ID
3. Cancelling appointments

You have access to the following doctors:
{doctors}

When collecting information to book an appointment, you need:
- Patient full name
- Patient phone number
- Patient EGN (10 digit Bulgarian ID)
- Doctor choice
- Preferred date (YYYY-MM-DD)
- Preferred time slot

Always respond in Bulgarian language.
Always respond ONLY in this JSON format:
{{
    "intent": "book" | "check" | "cancel" | "info" | "greeting" | "collect_info",
    "message": "Your response to the patient in Bulgarian",
    "data": {{}}
}}"""

class ChatRequest(BaseModel):
    message: str
    conversation_history: list = []

@router.post("/chat")
def chat(request: ChatRequest, db: Session = Depends(get_db)):
    # Get active doctors from database
    doctors = db.query(Doctor).filter(Doctor.is_active == True).all()
    doctors_info = "\n".join([
        f"- {d.name} ({d.specialty}) at {d.location}, {d.slot_minutes} min slots"
        for d in doctors
    ])

    # Build messages for OpenAI
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT.format(doctors=doctors_info)}
    ] + request.conversation_history + [
        {"role": "user", "content": request.message}
    ]

    # Call OpenAI
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        max_tokens=1000,
        messages=messages
    )

    ai_text = response.choices[0].message.content

    # Parse JSON response
    try:
        ai_data = json.loads(ai_text)
    except:
        ai_data = {
            "intent": "info",
            "message": ai_text,
            "data": {}
        }

    return {
        "response": ai_data.get("message", "Съжалявам, не разбрах. Моля, опитайте отново."),
        "intent": ai_data.get("intent", "info"),
        "data": ai_data.get("data", {})
    }