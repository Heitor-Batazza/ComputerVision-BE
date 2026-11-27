"""Servidor das voltas do chronométrage.

A câmera e os outros computadores da rede local enviam cada volta com POST /voltas.
A lista fica na memória e se perde quando o servidor é desligado.
Cada volta recebida também é acrescentada em data/resultados_video.csv.
Ainda não há autenticação: use apenas na rede do laboratório.
"""

import csv
import threading
from pathlib import Path

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

ARQUIVO_CSV = Path(__file__).resolve().parent.parent / "data" / "resultados_video.csv"
gravacao = threading.Lock()

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


def gravar_volta(dado):
    with gravacao:
        ARQUIVO_CSV.parent.mkdir(parents=True, exist_ok=True)
        novo = not ARQUIVO_CSV.exists() or ARQUIVO_CSV.stat().st_size == 0
        with open(ARQUIVO_CSV, "a", newline="", encoding="utf-8") as arquivo:
            escritor = csv.writer(arquivo)
            if novo:
                escritor.writerow(["Horario", "Metodo", "Carro_ID", "Volta", "Tempo_s"])
            escritor.writerow([
                dado["heure"], dado["metodo"], dado["voiture"], dado["tour"], dado["tempo"],
            ])


@app.post("/voltas")
def receber_volta(volta: Volta):
    dado = volta.model_dump()
    print("Volta recebida:", dado)
    voltas.append(dado)
    gravar_volta(dado)
    return dado


@app.get("/voltas")
def listar_voltas():
    return voltas


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
