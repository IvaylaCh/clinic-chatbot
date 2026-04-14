from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import get_db
from models import Doctor, Appointment, AvailabilityRule, AppointmentStatus, Service
from pydantic import BaseModel
from datetime import datetime, timedelta

class BookAppointmentRequest(BaseModel):
    doctor_id: int
    service_id: int
    patient_name: str
    patient_phone: str
    start_at: str  # "YYYY-MM-DD HH:MM"

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

#Get all services
@router.get("/services")
def get_services(db: Session = Depends(get_db)):
    services = db.query(Service).filter(Service.is_active == True).all()
    return [{"id": s.id, "name": s.name} for s in services]

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


# POST /api/appointments - book an appointment
@router.post("/appointments", status_code=201)
def book_appointment(data: BookAppointmentRequest, db: Session = Depends(get_db)):
    # Validate doctor exists
    doctor = db.query(Doctor).filter(Doctor.id == data.doctor_id, Doctor.is_active == True).first()
    if not doctor:
        raise HTTPException(status_code=404, detail="Doctor not found")

    # Parse start_at
    try:
        start_at = datetime.strptime(data.start_at, "%Y-%m-%d %H:%M")
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD HH:MM")

    # Check the slot is available on that weekday
    weekday = start_at.isoweekday()
    rule = db.query(AvailabilityRule).filter(
        AvailabilityRule.doctor_id == data.doctor_id,
        AvailabilityRule.weekday == weekday
    ).first()
    if not rule:
        raise HTTPException(status_code=400, detail="Doctor does not work on this day")

    # Check slot is not already booked
    conflict = db.query(Appointment).filter(
        Appointment.doctor_id == data.doctor_id,
        Appointment.start_at == start_at,
        Appointment.status == AppointmentStatus.BOOKED
    ).first()
    if conflict:
        raise HTTPException(status_code=409, detail="This slot is already booked")

    service = db.query(Service).filter(Service.id == data.service_id, Service.is_active == True).first()
    if not service:
        raise HTTPException(status_code=404, detail="Service not found")

    appointment = Appointment(
        doctor_id=data.doctor_id,
        service_id=data.service_id,
        patient_name=data.patient_name,
        patient_phone=data.patient_phone,
        start_at=start_at,
        status=AppointmentStatus.BOOKED,
        created_at=datetime.utcnow()
    )
    db.add(appointment)
    db.commit()
    db.refresh(appointment)

    return {
        "id": appointment.id,
        "doctor": doctor.name,
        "service": service.name,
        "patient_name": appointment.patient_name,
        "start_at": appointment.start_at.strftime("%Y-%m-%d %H:%M"),
        "status": appointment.status
    }


# GET /api/appointments/{id} - check an appointment
@router.get("/appointments/{appointment_id}")
def get_appointment(appointment_id: int, db: Session = Depends(get_db)):
    appointment = db.query(Appointment).filter(Appointment.id == appointment_id).first()
    if not appointment:
        raise HTTPException(status_code=404, detail="Appointment not found")

    return {
        "id": appointment.id,
        "doctor": appointment.doctor.name,
        "patient_name": appointment.patient_name,
        "patient_phone": appointment.patient_phone,
        "start_at": appointment.start_at.strftime("%Y-%m-%d %H:%M"),
        "status": appointment.status,
        "created_at": appointment.created_at.strftime("%Y-%m-%d %H:%M") if appointment.created_at else None
    }


# POST /api/appointments/{id}/cancel - cancel an appointment
@router.post("/appointments/{appointment_id}/cancel")
def cancel_appointment(appointment_id: int, db: Session = Depends(get_db)):
    appointment = db.query(Appointment).filter(Appointment.id == appointment_id).first()
    if not appointment:
        raise HTTPException(status_code=404, detail="Appointment not found")

    if appointment.status == AppointmentStatus.CANCELLED:
        raise HTTPException(status_code=400, detail="Appointment is already cancelled")

    if appointment.status == AppointmentStatus.COMPLETED:
        raise HTTPException(status_code=400, detail="Cannot cancel a completed appointment")

    appointment.status = AppointmentStatus.CANCELLED
    db.commit()

    return {
        "id": appointment.id,
        "status": appointment.status,
        "message": "Appointment cancelled successfully"
    }
