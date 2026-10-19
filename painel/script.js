// Escolhas atuais do formulário
let formatoEscolhido = "mp4";
let qualidadeEscolhida = "720p";

// ==========================================
// ABAS
// ==========================================
document.querySelectorAll(".aba").forEach((aba) => {
    aba.addEventListener("click", () => {
        document.querySelectorAll(".aba").forEach((a) => a.classList.remove("ativa"));
        aba.classList.add("ativa");
        document.getElementById("youtube").classList.toggle("escondido", aba.dataset.aba !== "youtube");
        document.getElementById("heic").classList.toggle("escondido", aba.dataset.aba !== "heic");
    });
});

// ==========================================
// FERRAMENTA 1: YOUTUBE
// ==========================================

// Formato (MP4 / MP3)
document.querySelectorAll("#formatos .chip").forEach((chip) => {
    chip.addEventListener("click", () => {
        document.querySelectorAll("#formatos .chip").forEach((c) => c.classList.remove("ativo"));
        chip.classList.add("ativo");
        formatoEscolhido = chip.dataset.formato;

        // Qualidade só vale para vídeo
        document.querySelectorAll("#qualidades .chip").forEach((c) => (c.disabled = formatoEscolhido === "mp3"));
    });
});

// Busca as qualidades na API e cria os botões
async function carregarQualidades() {
    const resposta = await fetch("/api/qualidades");
    const dados = await resposta.json();
    qualidadeEscolhida = dados.padrao;

    const grupo = document.getElementById("qualidades");
    dados.qualidades.forEach((qualidade) => {
        const chip = document.createElement("button");
        chip.type = "button";
        chip.className = "chip" + (qualidade === dados.padrao ? " ativo" : "");
        chip.textContent = qualidade;
        chip.addEventListener("click", () => {
            grupo.querySelectorAll(".chip").forEach((c) => c.classList.remove("ativo"));
            chip.classList.add("ativo");
            qualidadeEscolhida = qualidade;
        });
        grupo.appendChild(chip);
    });
}

// Envia o link para a fila
document.getElementById("form-download").addEventListener("submit", async (evento) => {
    evento.preventDefault();
    const campoUrl = document.getElementById("url");

    const resposta = await fetch("/api/download", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ url: campoUrl.value, formato: formatoEscolhido, qualidade: qualidadeEscolhida }),
    });
    const dados = await resposta.json();

    if (!resposta.ok) {
        alert(dados.erro);
        return;
    }

    criarItem(dados.id, formatoEscolhido === "mp3" ? "MP3" : `MP4 ${qualidadeEscolhida}`);
    campoUrl.value = "";
});

// Cria um item na lista e acompanha o progresso dele
function criarItem(id, descricao) {
    const item = document.createElement("li");
    item.className = "item";
    item.innerHTML = `
        <div class="item-topo">
            <span class="item-titulo">${descricao}</span>
            <span class="item-status">Na fila...</span>
        </div>
        <div class="barra"><div class="barra-preenchida"></div></div>
    `;
    document.getElementById("lista-downloads").prepend(item);

    const titulo = item.querySelector(".item-titulo");
    const status = item.querySelector(".item-status");
    const barra = item.querySelector(".barra-preenchida");

    const intervalo = setInterval(async () => {
        const dados = await (await fetch(`/api/progresso/${id}`)).json();
        status.textContent = dados.status;

        // "45.3%" -> barra em 45.3%
        if (dados.status.endsWith("%")) barra.style.width = dados.status;
        if (dados.status === "Processando arquivo...") barra.style.width = "100%";

        if (dados.status === "Pronto") {
            clearInterval(intervalo);
            barra.style.width = "100%";
            item.classList.add("pronto");
            titulo.textContent = `${dados.titulo} (${descricao})`;

            const link = document.createElement("a");
            link.href = `/api/arquivo/${id}`;
            link.textContent = "⬇ Salvar arquivo";
            link.addEventListener("click", () => {
                // O servidor apaga o arquivo depois do download
                setTimeout(() => link.replaceWith("Arquivo salvo ✓"), 500);
            });
            item.appendChild(link);
        }

        if (dados.status === "Erro" || dados.status === "Desconhecido") {
            clearInterval(intervalo);
            item.classList.add("erro");
            status.textContent = "Erro ao baixar";
        }
    }, 500);
}

// ==========================================
// FERRAMENTA 2: HEIC -> JPG
// ==========================================
const areaArquivo = document.getElementById("area-arquivo");
const campoArquivo = document.getElementById("arquivo-heic");
const statusHeic = document.getElementById("status-heic");

campoArquivo.addEventListener("change", () => {
    if (campoArquivo.files[0]) converterHeic(campoArquivo.files[0]);
});

// Arrastar e soltar
areaArquivo.addEventListener("dragover", (e) => {
    e.preventDefault();
    areaArquivo.classList.add("arrastando");
});
areaArquivo.addEventListener("dragleave", () => areaArquivo.classList.remove("arrastando"));
areaArquivo.addEventListener("drop", (e) => {
    e.preventDefault();
    areaArquivo.classList.remove("arrastando");
    if (e.dataTransfer.files[0]) converterHeic(e.dataTransfer.files[0]);
});

async function converterHeic(arquivo) {
    statusHeic.textContent = "Convertendo...";

    const formulario = new FormData();
    formulario.append("arquivo", arquivo);

    const resposta = await fetch("/api/converter/heic", { method: "POST", body: formulario });

    if (!resposta.ok) {
        statusHeic.textContent = (await resposta.json()).erro;
        return;
    }

    // Recebe o JPG e dispara o download no navegador
    const blob = await resposta.blob();
    const link = document.createElement("a");
    link.href = URL.createObjectURL(blob);
    link.download = arquivo.name.replace(/\.[^.]+$/, "") + ".jpg";
    link.click();
    URL.revokeObjectURL(link.href);

    statusHeic.textContent = `✓ ${link.download} convertido`;
    campoArquivo.value = "";
}

// ==========================================
// PROGRAMA: manter aberto / encerrar
// ==========================================

// Avisa o programa que o painel continua aberto. Sem esse aviso por 3 minutos
// (e sem downloads em andamento), o programa fecha sozinho.
function avisarQuePainelEstaAberto() {
    fetch("/api/ping", { method: "POST" }).catch(() => {});
}
avisarQuePainelEstaAberto();
setInterval(avisarQuePainelEstaAberto, 30000);

document.getElementById("encerrar").addEventListener("click", async () => {
    if (!confirm("Encerrar o programa? Downloads em andamento serão interrompidos.")) return;

    await fetch("/api/encerrar", { method: "POST" }).catch(() => {});
    document.body.innerHTML = `
        <div class="brilho"></div>
        <div class="encerrado">
            <h1>Programa encerrado</h1>
            <p>Pode fechar esta aba. Para usar de novo, abra o BaixarYouTube.exe.</p>
        </div>
    `;
});

carregarQualidades();
