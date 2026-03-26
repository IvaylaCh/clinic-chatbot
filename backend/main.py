from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from database  import engine, Base
from routes.appointments import router as appointments_router
from routes.chat import router as chat_router


app=FastAPI(title="Clinic Chatbot API")

app.include_router(chat_router)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # В продукция сложи само домейна на клиниката
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(appointments_router)

@app.get("/")
def root():
    return{"message":"API works"}

@app.get("/test-db")
def test_db():
    try:
        with engine.connect() as conn:
            return {"database": "connected!"}
    except Exception as e:
        return {"database": "failed", "error": str(e)}