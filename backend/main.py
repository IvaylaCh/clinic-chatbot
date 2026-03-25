from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from database import engine, Base
app=FastAPI()


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # В продукция сложи само домейна на клиниката
    allow_methods=["*"],
    allow_headers=["*"],
)

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