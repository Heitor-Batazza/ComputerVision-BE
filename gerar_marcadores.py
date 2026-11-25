import cv2

# Usa um dicionário leve de marcadores 4x4 (ótimo para leitura rápida em movimento)
dicionario = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_4X4_50)

for id_carro in range(3):
    imagem = cv2.aruco.generateImageMarker(dicionario, id_carro, 200)
    cv2.imwrite(f"carro_{id_carro}.png", imagem)

print("Marcadores gerados com sucesso!")