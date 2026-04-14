from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from pydantic import BaseModel
from database import get_db
from models import Doctor, Appointment, AvailabilityRule, Service
from openai import OpenAI
from datetime import datetime
import os
import json
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), '..', '..', '.env'))

router = APIRouter(prefix="/api", tags=["chat"])
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

today = datetime.now().strftime("%Y-%m-%d")
weekday_bg = ["Понеделник", "Вторник", "Сряда", "Четвъртък", "Петък", "Събота", "Неделя"]
today_name = weekday_bg[datetime.now().weekday()]

SYSTEM_PROMPT = f"""You are a helpful assistant for a medical clinic in Bulgaria.
Today is {today_name}, {today}.

You help patients with:
1. Booking appointments
2. Checking appointments by ID
3. Cancelling appointments

You have access to the following doctors:
{{doctors}}

Available services:
{{services}}

IMPORTANT: Before booking, always check if the doctor works on the requested day based on their schedule provided. If not, suggest the next available day.

When you have collected ALL information needed to book, return intent "book_ready" and include in data:
{{{{
    "doctor_id": <number>,
    "service_id": <number>,
    "patient_name": "<full name>",
    "patient_phone": "<phone>",
    "start_at": "<YYYY-MM-DD HH:MM>"
}}}}

When patient wants to check appointment, return intent "check" and data: {{{{"appointment_id": <number>}}}}
When patient wants to cancel appointment, return intent "cancel" and data: {{{{"appointment_id": <number>}}}}

Always respond in Bulgarian language.
Always respond ONLY in this JSON format:
{{{{
    "intent": "book" | "book_ready" | "check" | "cancel" | "info" | "greeting" | "collect_info",
    "message": "Your response to the patient in Bulgarian",
    "data": {{{{}}}}
}}}}"""

class ChatRequest(BaseModel):
    message: str
    conversation_history: list = []

@router.post("/chat")
def chat(request: ChatRequest, db: Session = Depends(get_db)):
    # Get active doctors from database
    doctors = db.query(Doctor).filter(Doctor.is_active == True).all()
    doctors_info = "\n".join([
        f"- {d.name} (ID:{d.id}, {d.specialty}) at {d.location}, {d.slot_minutes} min slots, works on weekdays: {[r.weekday for r in d.availability_rules]}"
        for d in doctors
    ])

    # Get active services from database
    services = db.query(Service).filter(Service.is_active == True).all()
    services_info = "\n".join([f"- {s.name} (ID:{s.id})" for s in services])

    # Build messages for OpenAI
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT.format(doctors=doctors_info, services=services_info)}
    ] + request.conversation_history + [
        {"role": "user", "content": request.message}
    ]

    # Call OpenAI
    response = client.chat.completions.create(
        model="gpt-4o",
        max_tokens=1000,
        messages=messages
    )

    ai_text = response.choices[0].message.content

    # Parse JSON response
    try:
        # Strip markdown code blocks if present
        clean_text = ai_text.strip()
        if clean_text.startswith("```"):
            clean_text = clean_text.split("```")[1]
            if clean_text.startswith("json"):
                clean_text = clean_text[4:]
        ai_data = json.loads(clean_text.strip())
    except:
        ai_data = {
            "intent": "info",
            "message": ai_text,
            "data": {}
        }

    intent = ai_data.get("intent")
    data = ai_data.get("data", {})
    message = ai_data.get("message", "Съжалявам, не разбрах.")

    # AUTO BOOK when AI has collected all info
    if intent == "book_ready":
        try:
            doctor = db.query(Doctor).filter(Doctor.id == data["doctor_id"]).first()
            appointment = Appointment(
                doctor_id=data["doctor_id"],
                service_id=data["service_id"],
                patient_name=data["patient_name"],
                patient_phone=data["patient_phone"],
                start_at=datetime.strptime(data["start_at"], "%Y-%m-%d %H:%M"),
                status="BOOKED",
                created_at=datetime.utcnow()
            )
            db.add(appointment)
            db.commit()
            db.refresh(appointment)
            return {
                "response": f" Часът е запазен успешно при {doctor.name}! Вашият код е #{appointment.id}. Запазете го за проверка.",
                "intent": "book_confirmed",
                "appointment_id": appointment.id
            }
        except Exception as e:
            return {
                "response": "Съжалявам, възникна грешка при запазването. Моля, опитайте отново.",
                "intent": "error",
                "data": {}
            }

    # AUTO CHECK
    if intent == "check" and "appointment_id" in data:
        appointment = db.query(Appointment).filter(
            Appointment.id == data["appointment_id"]
        ).first()
        if appointment:
            return {
                "response": f"Намерих Вашия час:\n {appointment.patient_name}\n {appointment.doctor.name}\n Услуга: {appointment.service.name}\n {appointment.start_at.strftime('%Y-%m-%d %H:%M')}\n Статус: {appointment.status.value}",
                "intent": "check_result",
                "data": {}
            }
        else:
            return {
                "response": f"Не намерих час с код #{data['appointment_id']}.",
                "intent": "not_found",
                "data": {}
            }

    # AUTO CANCEL
    if intent == "cancel" and "appointment_id" in data:
        appointment = db.query(Appointment).filter(
            Appointment.id == data["appointment_id"]
        ).first()
        if appointment:
            appointment.status = "CANCELLED"
            db.commit()
            return {
                "response": f"Часът #{data['appointment_id']} е отказан успешно.",
                "intent": "cancel_confirmed",
                "data": {}
            }

    return {
        "response": message,
        "intent": intent,
        "data": data
    }