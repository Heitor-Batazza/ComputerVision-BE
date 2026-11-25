const status = document.getElementById("status");
const ws = new WebSocket("ws://127.0.0.1:8000/ws");

ws.onmessage = (evento) => {
    const dado = JSON.parse(evento.data);
    const titulo = status.firstElementChild;

    status.replaceChildren(titulo);
    for (const linha of dado.texto.split("\n")) {
        if (!linha.startsWith("Carro ")) {
            continue;
        }
        const p = document.createElement("p");
        p.textContent = linha;
        status.appendChild(p);
    }
};
