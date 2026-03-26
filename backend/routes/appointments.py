from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import get_db
from models import Doctor, Appointment, AvailabilityRule, AppointmentStatus
from pydantic import BaseModel
from datetime import datetime, timedelta

router= APIRouter(prefix="/api", tags=["appointments"])

#Get all doctors
@router.get("/doctors")
def get_doctors(db:Session=Depends(get_db)):
       doctors = db.query(Doctor).filter(Doctor.is_active == True).all()
       return [
                {
                    "id": d.id,
                    "name": d.name,
                    "specialty": d.specialty,
                    "location": d.location,
                    "slot_minutes": d.slot_minutes
                }
                for d in doctors
            ]

#get available slots 
@router.get("/doctors/{doctor_id}/slots")
def get_slots(doctor_id: int, date: str, db:Session=Depends(get_db)):
       
    # Step 1 - get the doctor
    doctor = db.query(Doctor).filter(Doctor.id == doctor_id).first()
    if not doctor:
        raise HTTPException(status_code=404, detail="Doctor not found")
    
    # Step 2 - parse the date and get weekday (0=Monday, 6=Sunday)
    appointment_date=datetime.strptime(date,"%Y-%m-%d")
    weekday=appointment_date.isoweekday()

    # Step 3 - check if doctor works on this weekday
    rule=db.query(AvailabilityRule).filter(AvailabilityRule.doctor_id==doctor_id,
                AvailabilityRule.weekday==weekday).first()
    if not rule:
        return {"available_slots": [], "message": "Doctor does not work on this day"}
    
    # Step 4 - generate all possible slots
    all_slots = []
    current = datetime.combine(appointment_date.date(), rule.start_time)
    end = datetime.combine(appointment_date.date(), rule.end_time)
    
    while current < end:
        all_slots.append(current)
        current += timedelta(minutes=doctor.slot_minutes)
    
    # Step 5 - get already booked slots
    booked = db.query(Appointment).filter(
        Appointment.doctor_id == doctor_id,
        Appointment.start_at >= appointment_date,
        Appointment.start_at < appointment_date + timedelta(days=1),
        Appointment.status=="BOOKED"
    ).all()
    
    booked_times = [a.start_at for a in booked]
    
    # Step 6 - return only free slots
    free_slots = [
        slot.strftime("%H:%M")
        for slot in all_slots
        if slot not in booked_times
    ]
    
    return {
        "doctor": doctor.name,
        "date": date,
        "available_slots": free_slots
    }
