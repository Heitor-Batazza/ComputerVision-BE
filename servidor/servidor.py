"""Servidor das voltas do chronométrage.

A câmera e os outros computadores da rede local enviam cada volta com POST /voltas.
A lista fica só na memória e se perde quando o servidor é desligado.
Ainda não há autenticação: use apenas na rede do laboratório.
"""

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

app = FastAPI()
# A página é aberta como arquivo local. Sem isto, o navegador bloqueia o GET /voltas.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)
voltas = []


class Volta(BaseModel):
    metodo: str = "teste"
    voiture: int = 0
    tour: int = 0
    tempo: str = "--"
    heure: str = "--"


@app.get("/")
@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/voltas")
def receber_volta(volta: Volta):
    dado = volta.model_dump()
    print("Volta recebida:", dado)
    voltas.append(dado)
    return dado


@app.get("/voltas")
def listar_voltas():
    return voltas


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
