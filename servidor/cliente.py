"""Envia uma volta de teste para o servidor.

No computador do colega, mantenha o IP deste PC na rede local.
"""

import json
import urllib.request

URL = "http://172.18.0.35:8000/voltas"
# URL = "http://127.0.0.1:8000/voltas"

volta = {
    "metodo": "FluxVideo",
    "voiture": 0,
    "tour": 1,
    "tempo": "5.420",
    "heure": "16:40:00.000",
}

pedido = urllib.request.Request(
    URL,
    data=json.dumps(volta).encode("utf-8"),
    headers={"Content-Type": "application/json"},
)

with urllib.request.urlopen(pedido) as resposta:
    print(resposta.read().decode("utf-8"))
