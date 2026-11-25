import asyncio
import csv
import threading
import time
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path

import cv2
import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect

CAMERA = 0
LARGURA, ALTURA, FPS = 1280, 720, 60
EXPOSICAO = -7
FAIXA = 0.8
TEMPO_MINIMO_VOLTA = 1.5
INTERVALO_MAXIMO = 0.25
MOSTRAR_JANELA = True
ARQUIVO_CSV = Path(__file__).resolve().parent / "data" / "resultados_video.csv"

placar = []
clientes = set()
loop_servidor = None
servidor_pronto = threading.Event()


@asynccontextmanager
async def ciclo_de_vida(app):
    global loop_servidor
    loop_servidor = asyncio.get_running_loop()
    servidor_pronto.set()
    yield


app = FastAPI(lifespan=ciclo_de_vida)


@app.websocket("/ws")
async def conexao(websocket: WebSocket):
    await websocket.accept()
    fila = asyncio.Queue()
    if placar:
        fila.put_nowait(placar)
    clientes.add(fila)
    try:
        while True:
            await websocket.send_json({"carros": await fila.get()})
    except WebSocketDisconnect:
        pass
    finally:
        clientes.discard(fila)


def distribuir(carros):
    global placar
    placar = carros
    for fila in clientes:
        fila.put_nowait(carros)


def publicar(carros):
    loop_servidor.call_soon_threadsafe(distribuir, carros)

def abrir_camera():
    cap = cv2.VideoCapture(CAMERA, cv2.CAP_DSHOW)
    if not cap.isOpened():
        raise SystemExit(f"Não foi possível abrir a câmera {CAMERA}.")
    #cap.set(cv2.CAP_PROP_FPS, FPS)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, LARGURA)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, ALTURA)
    cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*"MJPG"))
    cap.set(cv2.CAP_PROP_AUTOFOCUS, 0)
    cap.set(cv2.CAP_PROP_AUTO_EXPOSURE, 0.25)
    cap.set(cv2.CAP_PROP_EXPOSURE, EXPOSICAO)
    print("Câmera:", cap.get(cv2.CAP_PROP_FRAME_WIDTH), "x",
        cap.get(cv2.CAP_PROP_FRAME_HEIGHT), "a", cap.get(cv2.CAP_PROP_FPS), "FPS")
    return cap

def rodar_camera():
    dicionario = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_4X4_50)
    detector = cv2.aruco.ArucoDetector(dicionario, cv2.aruco.DetectorParameters())
    anterior = {}
    inicio_volta = {}
    voltas = {}
    melhor_volta = {}
    ultimo_tempo = {}
    horario = {}

    def classificacao():
        ordem = sorted(voltas, key=lambda c: (-voltas[c], inicio_volta[c]))
        return [{
            "carro": c,
            "volta": voltas[c],
            "ultimo": f"{ultimo_tempo[c]:.3f}" if c in ultimo_tempo else "--",
            "melhor": f"{melhor_volta[c]:.3f}" if c in melhor_volta else "--",
            "horario": horario.get(c, "--"),
        } for c in ordem]

    cap = abrir_camera()
    ARQUIVO_CSV.parent.mkdir(parents=True, exist_ok=True)
    try:
        with open(ARQUIVO_CSV, "w", newline="", encoding="utf-8") as arquivo:
            escritor = csv.writer(arquivo)
            escritor.writerow(["Horario", "Metodo", "Carro_ID", "Volta", "Tempo_s"])

            while True:
                ret, frame = cap.read()
                agora = time.perf_counter()
                if not ret:
                    break

                largura = frame.shape[1]
                x0 = int(largura * (1 - FAIXA) / 2)
                linha_x = largura / 2 - x0
                cinza = cv2.cvtColor(frame[:, x0:largura - x0], cv2.COLOR_BGR2GRAY)
                cantos, ids, _ = detector.detectMarkers(cinza)

                if ids is not None:
                    for canto, carro in zip(cantos, ids.ravel().tolist()):
                        x = float(canto[0][:, 0].mean())
                        antes = anterior.get(carro)
                        anterior[carro] = (x, agora)

                        if antes is None or agora - antes[1] > INTERVALO_MAXIMO:
                            continue
                        x_antes, t_antes = antes
                        if not x_antes < linha_x <= x:
                            continue

                        # Instante estimado em que o centro tocou a linha
                        fracao = (linha_x - x_antes) / (x - x_antes)
                        t = t_antes + fracao * (agora - t_antes)

                        if carro not in inicio_volta:
                            inicio_volta[carro] = t
                            voltas[carro] = 0
                            publicar(classificacao())
                            continue

                        duracao = t - inicio_volta[carro]
                        if duracao <= TEMPO_MINIMO_VOLTA:
                            continue  # não reinicia o cronômetro

                        inicio_volta[carro] = t
                        voltas[carro] += 1
                        melhor_volta[carro] = min(duracao, melhor_volta.get(carro, duracao))
                        ultimo_tempo[carro] = duracao
                        horario[carro] = datetime.now().strftime("%H:%M:%S.%f")[:-3]
                        publicar(classificacao())
                        escritor.writerow([horario[carro],
                                        "Video_ArUco", carro, voltas[carro], f"{duracao:.4f}"])
                        arquivo.flush()

                if MOSTRAR_JANELA:
                    if ids is not None:
                        for canto in cantos:
                            pontos = canto[0].astype(int) + (x0, 0)
                            cv2.polylines(frame, [pontos], True, (0, 255, 0), 2)
                    cv2.line(frame, (largura // 2, 0), (largura // 2, frame.shape[0]), (0, 0, 255), 1)
                    cv2.imshow("Camera", frame)
                    if cv2.waitKey(1) & 0xFF == ord("q"):
                        break
    except KeyboardInterrupt:
        pass
    finally:
        cap.release()
        cv2.destroyAllWindows()


def subir_servidor():
    uvicorn.run(app, host="127.0.0.1", port=8000)


if __name__ == "__main__":
    threading.Thread(target=subir_servidor, daemon=True).start()
    if not servidor_pronto.wait(timeout=10):
        raise SystemExit("O servidor não iniciou. A porta 8000 está em uso?")
    rodar_camera()