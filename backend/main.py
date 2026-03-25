from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

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

@app.get("/health")
def health():
    return {"status": "ok"}