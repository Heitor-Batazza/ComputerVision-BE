const status = document.getElementById("status");
const ws = new WebSocket("ws://127.0.0.1:8000/ws");
const linhas = {};

ws.onmessage = (evento) => {
    const dado = JSON.parse(evento.data);
    const carro = dado.texto[6];

    if (!linhas[carro]) {
        linhas[carro] = document.createElement("p");
        status.appendChild(linhas[carro]);
    }
    linhas[carro].textContent = dado.texto;
};
