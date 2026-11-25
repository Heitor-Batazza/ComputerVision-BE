"""Envia uma volta de teste para o servidor.

No computador do colega, troque 127.0.0.1 pelo IP deste PC na rede local.
"""

import json
import urllib.request

URL = "http://172.18.0.84:8000/voltas"

volta = {
    "metodo": "tracker",
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
