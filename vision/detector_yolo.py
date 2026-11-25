"""Cronometragem por video com YOLO, no mesmo criterio do script ArUco.

Os IDs vem do rastreador, nao dos marcadores impressos. O modelo yolo11n
foi treinado com objetos do cotidiano; um Mini-Z pode nao ser classificado
como carro. CLASSES = None segue qualquer objeto para testar a linha.
"""

import csv
import math
import os
import time
from datetime import datetime
from pathlib import Path

import cv2

# Impede o ultralytics de instalar opencv-python por conta propria.
# Esse pacote substituiria o opencv-contrib e o ArUco deixaria de existir.
os.environ["YOLO_AUTOINSTALL"] = "0"

try:
    import torch
    from ultralytics import YOLO
except ImportError:
    print("Falta o pacote ultralytics neste ambiente.")
    print("Instale com: .\\.venv\\Scripts\\python.exe -m pip install -r requirements.txt")
    raise SystemExit(1)

RAIZ = Path(__file__).resolve().parent.parent
PASTA_DATA = RAIZ / "data"
ARQUIVO_CSV = PASTA_DATA / "resultados_yolo.csv"
MODELO = RAIZ / "yolo11n.pt"

# 1 foi a camera que abriu a Logitech neste PC. Use 0 para a camera padrao.
INDICE_CAMERA = 1
# None segue qualquer objeto. (2,) restringe a classe "car" do COCO.
CLASSES = None
CONFIANCA = 0.25
IMGSZ = 640
DEBOUNCE_S = 1.5
DISTANCIA_TROCA_PX = 80
FRAMES_TROCA = 15

CORES = (
    (0, 255, 0),
    (255, 180, 0),
    (0, 180, 255),
    (255, 0, 180),
    (180, 255, 0),
)


def contar_troca(historico, centros_atuais, frame_idx):
    """Conta um ID switch quando um ID novo surge perto de um ID que sumiu."""
    trocas = 0
    perdidos = [
        (antigo, info)
        for antigo, info in historico.items()
        if antigo not in centros_atuais and frame_idx - info["frame"] <= FRAMES_TROCA
    ]
    for tid, (cx, cy) in centros_atuais.items():
        if tid not in historico:
            candidato = None
            menor = DISTANCIA_TROCA_PX
            for antigo, info in perdidos:
                dist = math.hypot(cx - info["cx"], cy - info["cy"])
                if dist <= menor:
                    menor = dist
                    candidato = antigo
            if candidato is not None:
                trocas += 1
                del historico[candidato]
                perdidos = [item for item in perdidos if item[0] != candidato]
        historico[tid] = {"cx": cx, "cy": cy, "frame": frame_idx}
    for antigo in [
        i for i, info in historico.items() if frame_idx - info["frame"] > FRAMES_TROCA
    ]:
        del historico[antigo]
    return trocas


def main():
    if not MODELO.is_file():
        print(f"Baixando {MODELO.name}. Isso acontece so na primeira execucao.")

    dispositivo = 0 if torch.cuda.is_available() else "cpu"
    print(f"Carregando {MODELO.name} em {dispositivo}.")
    modelo = YOLO(str(MODELO))

    cap = cv2.VideoCapture(INDICE_CAMERA)
    cap.set(cv2.CAP_PROP_AUTO_EXPOSURE, 0.25)
    cap.set(cv2.CAP_PROP_FPS, 60)
    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
    if not cap.isOpened():
        cap.release()
        print(f"Nao foi possivel abrir a camera {INDICE_CAMERA}.")
        raise SystemExit(1)

    PASTA_DATA.mkdir(parents=True, exist_ok=True)
    arquivo = ARQUIVO_CSV.open("w", newline="", encoding="utf-8")
    escritor = csv.writer(arquivo)
    escritor.writerow(
        [
            "timestamp_sistema",
            "metodo",
            "carro_id",
            "numero_volta",
            "tempo_volta_s",
            "fps_ou_latencia_ms",
        ]
    )
    arquivo.flush()

    pos_anterior_x = {}
    inicio_volta = {}
    voltas = {}
    melhor_volta = {}
    ultimo_tempo = {}
    historico = {}
    trocas = 0
    frame_idx = 0
    tempo_frame_anterior = time.perf_counter()

    print(f"Gravando voltas em {ARQUIVO_CSV}")
    print("Aperte q para fechar.")

    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                print("A camera parou de entregar quadros.")
                break

            agora_frame = time.perf_counter()
            intervalo_s = agora_frame - tempo_frame_anterior
            fps = 1.0 / intervalo_s if intervalo_s > 0 else 0.0
            latencia_ms = intervalo_s * 1000.0
            tempo_frame_anterior = agora_frame
            frame_idx += 1

            altura, largura = frame.shape[:2]
            linha_x = largura // 2
            cv2.line(frame, (linha_x, 0), (linha_x, altura), (0, 0, 255), 3)
            cv2.putText(
                frame,
                f"FPS: {fps:.1f}",
                (10, 30),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.8,
                (0, 255, 255),
                2,
            )
            cv2.putText(
                frame,
                f"Trocas de ID: {trocas}",
                (10, 60),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.7,
                (0, 255, 255),
                2,
            )

            opcoes = {
                "persist": True,
                "verbose": False,
                "tracker": "bytetrack.yaml",
                "conf": CONFIANCA,
                "imgsz": IMGSZ,
                "device": dispositivo,
            }
            if CLASSES is not None:
                opcoes["classes"] = CLASSES
            resultados = modelo.track(frame, **opcoes)
            deteccoes = resultados[0]

            centros_atuais = {}
            caixas = deteccoes.boxes
            if caixas is not None and len(caixas) > 0 and caixas.id is not None:
                ids = caixas.id.cpu().numpy().astype(int)
                xyxy = caixas.xyxy.cpu().numpy()
                classes = caixas.cls.cpu().numpy().astype(int)
                nomes = deteccoes.names

                for i, identificador in enumerate(ids):
                    tid = int(identificador)
                    x1, y1, x2, y2 = (int(v) for v in xyxy[i])
                    cx = (x1 + x2) // 2
                    cy = (y1 + y2) // 2
                    centros_atuais[tid] = (cx, cy)
                    cor = CORES[tid % len(CORES)]
                    nome = nomes.get(int(classes[i]), "")
                    cv2.rectangle(frame, (x1, y1), (x2, y2), cor, 2)
                    cv2.circle(frame, (cx, cy), 5, cor, -1)
                    cv2.putText(
                        frame,
                        f"id={tid} {nome}",
                        (x1, max(20, y1 - 8)),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.6,
                        cor,
                        2,
                    )

                    # Mesma regra do ArUco: esquerda para a direita.
                    # A primeira passagem so arma o cronometro.
                    if tid in pos_anterior_x and pos_anterior_x[tid] < linha_x <= cx:
                        t_cruzamento = time.perf_counter()
                        if tid in inicio_volta:
                            duracao = t_cruzamento - inicio_volta[tid]
                            if duracao > DEBOUNCE_S:
                                voltas[tid] = voltas.get(tid, 0) + 1
                                ultimo_tempo[tid] = duracao
                                if tid not in melhor_volta or duracao < melhor_volta[tid]:
                                    melhor_volta[tid] = duracao
                                escritor.writerow(
                                    [
                                        datetime.now().isoformat(timespec="milliseconds"),
                                        "VIDEO_YOLO",
                                        tid,
                                        voltas[tid],
                                        f"{duracao:.4f}",
                                        f"{latencia_ms:.1f}",
                                    ]
                                )
                                arquivo.flush()
                        else:
                            voltas[tid] = 0
                        inicio_volta[tid] = t_cruzamento
                    pos_anterior_x[tid] = cx

            trocas += contar_troca(historico, centros_atuais, frame_idx)

            y_texto = 100
            for cid in sorted(voltas):
                ult = f"{ultimo_tempo[cid]:.3f}s" if cid in ultimo_tempo else "--"
                mel = f"{melhor_volta[cid]:.3f}s" if cid in melhor_volta else "--"
                texto = f"ID {cid} | Voltas: {voltas[cid]} | Ult: {ult} | Melhor: {mel}"
                cv2.putText(
                    frame,
                    texto,
                    (10, y_texto),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.6,
                    (255, 255, 255),
                    2,
                )
                y_texto += 30

            cv2.imshow("Cronometro - YOLO", frame)
            if cv2.waitKey(1) & 0xFF == ord("q"):
                break
    finally:
        arquivo.close()
        cap.release()
        cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
