const linhas = document.getElementById("linhas");

function comparar(a, b) {
    if (a.volta !== b.volta) return b.volta - a.volta;
    if (a.horario === "--" && b.horario === "--") return a.carro - b.carro;
    if (a.horario === "--") return 1;
    if (b.horario === "--") return -1;
    if (a.horario !== b.horario) return a.horario < b.horario ? -1 : 1;
    return a.carro - b.carro;
}

function placar(voltas) {
    const porCarro = new Map();
    for (const id of [0, 1, 2]) {
        porCarro.set(id, { carro: id, volta: 0, ultimo: "--", horario: "--" });
    }

    for (const volta of voltas) {
        if (volta.metodo !== "Video_ArUco") continue;
        if (!porCarro.has(volta.voiture)) {
            porCarro.set(volta.voiture, {
                carro: volta.voiture,
                volta: 0,
                ultimo: "--",
                horario: "--",
            });
        }
        const atual = porCarro.get(volta.voiture);
        if (volta.tour > atual.volta) {
            atual.volta = volta.tour;
            atual.ultimo = volta.tempo;
            atual.horario = volta.heure;
        }
    }

    return [...porCarro.values()].sort(comparar);
}

function desenhar(carros) {
    linhas.replaceChildren();
    for (const carro of carros) {
        const tr = document.createElement("tr");
        for (const campo of ["carro", "volta", "ultimo", "horario"]) {
            const td = document.createElement("td");
            td.textContent = carro[campo];
            tr.appendChild(td);
        }
        linhas.appendChild(tr);
    }
}

async function atualizar() {
    try {
        const resposta = await fetch("http://172.18.0.35:8000/voltas");
        if (!resposta.ok) return;
        desenhar(placar(await resposta.json()));
    } catch {
        // O servidor pode estar desligado. A tabela fica como está.
    }
}

atualizar();
setInterval(atualizar, 1000);
