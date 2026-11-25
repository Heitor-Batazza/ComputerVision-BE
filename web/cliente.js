const painel = document.getElementById("status");
const ws = new WebSocket("ws://127.0.0.1:8000/ws");
const linhas = {};
const formatar = (s) => (s === null ? "--" : `${s.toFixed(3)}s`);

ws.onmessage = (evento) => {
  const d = JSON.parse(evento.data);
  if (!linhas[d.carro]) {
    linhas[d.carro] = document.createElement("p");
    painel.appendChild(linhas[d.carro]);
  }
  linhas[d.carro].textContent =
    `Carro ${d.carro} | Voltas: ${d.voltas} | Último: ${formatar(d.ultimo)} | Melhor: ${formatar(d.melhor)}`;
};
