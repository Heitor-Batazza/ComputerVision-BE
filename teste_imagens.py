import cv2
import time
import csv
from datetime import datetime
import asyncio
from fastapi import FastAPI, WebSocket
import uvicorn
import threading

texto = "Aguardando primeira volta"


app = FastAPI()

@app.websocket("/ws")
async def conexao(websocket: WebSocket):
    await websocket.accept()
    texto_anterior = ""
    while True:
        if texto != texto_anterior:
            texto_anterior = texto
            await websocket.send_json({"texto": texto})
        await asyncio.sleep(1)

# Configura a câmera (tenta forçar 60 FPS na Logitech BRIO)
def rodar_camera():
    global texto
    cap = cv2.VideoCapture(1)
    cap.set(cv2.CAP_PROP_AUTO_EXPOSURE, 0.25)
    cap.set(cv2.CAP_PROP_EXPOSURE, -6)
    cap.set(cv2.CAP_PROP_AUTOFOCUS, 0)
    cap.set(cv2.CAP_PROP_FPS, 60)

    dicionario = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_4X4_50)
    detector = cv2.aruco.ArucoDetector(dicionario, cv2.aruco.DetectorParameters())

    # Estado dos carrinhos
    pos_anterior_x = {}
    inicio_volta = {}
    voltas = {}
    melhor_volta = {}
    ultimo_tempo = {}

    # Prepara o arquivo CSV para salvar os dados da comparação
    arquivo_csv = "resultados_video.csv"
    with open(arquivo_csv, mode="w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["Horario", "Metodo", "Carro_ID", "Volta", "Tempo_s"])

    tempo_frame_anterior = time.perf_counter()

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        # Calcula o FPS atual
        agora_frame = time.perf_counter()
        fps = 1.0 / (agora_frame - tempo_frame_anterior)
        tempo_frame_anterior = agora_frame

        altura, largura, _ = frame.shape
        linha_x = largura // 2  # Linha de chegada no meio da tela

        # Desenha a linha de chegada e o FPS
        cv2.line(frame, (linha_x, 0), (linha_x, altura), (0, 0, 255), 3)
        cv2.putText(frame, f"FPS: {fps:.1f}", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 255), 2)

        cantos, ids, _ = detector.detectMarkers(frame)

        if ids is not None:
            cv2.aruco.drawDetectedMarkers(frame, cantos)

            for i, id_array in enumerate(ids):
                carro_id = int(id_array)
                pontos = cantos[i][0]
                cx = int(pontos[:, 0].mean())
                cy = int(pontos[:, 1].mean())

                cv2.circle(frame, (cx, cy), 6, (0, 255, 0), -1)

                # Detecta cruzamento da esquerda para a direita
                if carro_id in pos_anterior_x:
                    if pos_anterior_x[carro_id] < linha_x and cx >= linha_x:
                        t_cruzamento = time.perf_counter()

                        if carro_id in inicio_volta:
                            duracao = t_cruzamento - inicio_volta[carro_id]
                            
                            # Filtro simples para evitar leitura dupla acidental (< 1.5s)
                            if duracao > 1.5:
                                voltas[carro_id] = voltas.get(carro_id, 0) + 1
                                ultimo_tempo[carro_id] = duracao
                                
                                if carro_id not in melhor_volta or duracao < melhor_volta[carro_id]:
                                    melhor_volta[carro_id] = duracao

                                # Salva no CSV
                                with open(arquivo_csv, mode="a", newline="") as f:
                                    writer = csv.writer(f)
                                    writer.writerow([datetime.now().strftime("%H:%M:%S.%f")[:-3], 
                                                    "Video_ArUco", carro_id, voltas[carro_id], f"{duracao:.4f}"])
                        else:
                            voltas[carro_id] = 0

                        inicio_volta[carro_id] = t_cruzamento

                pos_anterior_x[carro_id] = cx

        # Desenha o placar no canto superior esquerdo
        y_texto = 70
        for cid in sorted(voltas.keys()):
            ult = f"{ultimo_tempo[cid]:.3f}s" if cid in ultimo_tempo else "--"
            mel = f"{melhor_volta[cid]:.3f}s" if cid in melhor_volta else "--"
            texto = f"Carro {cid} | Voltas: {voltas[cid]} | Ult: {ult} | Melhor: {mel}"
            cv2.putText(frame, texto, (10, y_texto), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
            y_texto += 30

        cv2.imshow("Cronometro - Fluxo de Video", frame)

        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()

def subir_servidor():
    uvicorn.run(app, host="127.0.0.1", port=8000)

threading.Thread(target=subir_servidor, daemon=True).start()
rodar_camera()
