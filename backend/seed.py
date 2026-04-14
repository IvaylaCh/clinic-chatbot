import sys
import os
sys.path.append(os.path.dirname(__file__))

from database import SessionLocal, engine
from models import Base, Doctor, AvailabilityRule, Service
from datetime import time

Base.metadata.create_all(bind=engine)

db = SessionLocal()

# Services
services = [
    Service(name="Първичен преглед", is_active=True),
    Service(name="Вторичен преглед", is_active=True),
]
db.add_all(services)
db.commit()

# Doctors
ivan = Doctor(
    name="Д-р Иван Иванов",
    specialty="Кардиолог",
    location="Кабинет 1",
    slot_minutes=30,
    is_active=True
)
db.add(ivan)
db.commit()
db.refresh(ivan)

# Availability: Monday=1, Wednesday=3, 09:00-13:00
rules = [
    AvailabilityRule(doctor_id=ivan.id, weekday=1, start_time=time(9, 0), end_time=time(13, 0)),
    AvailabilityRule(doctor_id=ivan.id, weekday=3, start_time=time(9, 0), end_time=time(13, 0)),
]
db.add_all(rules)
db.commit()

db.close()
print("Seed completed successfully!")
