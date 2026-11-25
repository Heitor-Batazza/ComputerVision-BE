const linhas = document.getElementById("linhas");
const ws = new WebSocket("ws://127.0.0.1:8000/ws");

ws.onmessage = (evento) => {
    const dado = JSON.parse(evento.data);
    linhas.replaceChildren();

    for (const carro of dado.carros) {
        const tr = document.createElement("tr");
        for (const campo of ["carro", "volta", "ultimo", "horario"]) {
            const td = document.createElement("td");
            td.textContent = carro[campo];
            tr.appendChild(td);
        }
        linhas.appendChild(tr);
    }
};
