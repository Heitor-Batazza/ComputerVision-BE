import json
import time
import urllib.error
import urllib.request
from datetime import datetime
import cv2

CAMERA = 0
LARGURA, ALTURA, FPS = 1280, 720, 60
EXPOSICAO = -7
FAIXA = 0.8
TEMPO_MINIMO_VOLTA = 1.5
INTERVALO_MAXIMO = 0.25
MOSTRAR_JANELA = True
# O servidor deste computador escuta na rede, mas a câmera fala com ele por aqui.
URL_VOLTAS = "http://127.0.0.1:8000/voltas"


def enviar_volta(carro, volta, tempo, hora):
    corpo = json.dumps({
        "metodo": "Video_ArUco",
        "voiture": carro,
        "tour": volta,
        "tempo": tempo,
        "heure": hora,
    }).encode("utf-8")
    pedido = urllib.request.Request(
        URL_VOLTAS,
        data=corpo,
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(pedido, timeout=0.5) as resposta:
            resposta.read()
    except (urllib.error.URLError, TimeoutError) as erro:
        print("Não foi possível enviar a volta:", erro)


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

    cap = abrir_camera()
    try:
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
                        continue

                    duracao = t - inicio_volta[carro]
                    if duracao <= TEMPO_MINIMO_VOLTA:
                        continue  # não reinicia o cronômetro

                    inicio_volta[carro] = t
                    voltas[carro] += 1
                    hora = datetime.now().strftime("%H:%M:%S.%f")[:-3]
                    tempo = f"{duracao:.4f}"
                    enviar_volta(carro, voltas[carro], tempo, hora)

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


if __name__ == "__main__":
    rodar_camera()
