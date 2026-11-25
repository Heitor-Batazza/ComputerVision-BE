"""Servidor provisório para testar um POST entre dois computadores.

Esta pasta é um experimento. Apague experimentos/servidor_rede para removê-lo.
Não ligue este servidor junto com teste_imagens.py: os dois usam a porta 8000.
Ele escuta em todas as interfaces da rede local. Não exponha esta porta na internet.
"""

import uvicorn
from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI()
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
