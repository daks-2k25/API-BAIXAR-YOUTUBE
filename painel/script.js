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

// ==========================================
// AVISO DE PLAYLIST
// ==========================================
const campoUrl = document.getElementById("url");
const botaoBaixar = document.querySelector("#form-download .botao");
const avisoPlaylist = document.getElementById("aviso-playlist");
const avisoTexto = document.getElementById("aviso-texto");
const botaoUsarSoVideo = document.getElementById("usar-so-video");

// Diz se o link é de uma playlist inteira, de um vídeo dentro de uma playlist
// ou de um vídeo comum. Para o vídeo dentro da playlist, devolve o link limpo.
function analisarLink(texto) {
    let link;
    try {
        link = new URL(texto.trim());
    } catch {
        return { tipo: "comum" };
    }
    if (!link.searchParams.has("list")) return { tipo: "comum" };

    const temVideo =
        link.searchParams.has("v") ||
        (link.hostname.endsWith("youtu.be") && link.pathname.length > 1) ||
        /^\/(shorts|live|embed)\//.test(link.pathname);

    if (!temVideo) return { tipo: "playlist" };

    ["list", "index", "start_radio", "pp"].forEach((p) => link.searchParams.delete(p));
    return { tipo: "video-na-playlist", linkLimpo: link.toString() };
}

function atualizarAvisoPlaylist() {
    const analise = analisarLink(campoUrl.value);
    const bloquear = analise.tipo !== "comum";

    avisoPlaylist.classList.toggle("escondido", !bloquear);
    botaoBaixar.disabled = bloquear;

    if (analise.tipo === "playlist") {
        avisoTexto.textContent =
            "⚠ Este link é de uma playlist. Playlists não podem ser baixadas: abra um vídeo da playlist e cole o link dele.";
        botaoUsarSoVideo.classList.add("escondido");
    }
    if (analise.tipo === "video-na-playlist") {
        avisoTexto.textContent = "⚠ Este vídeo faz parte de uma playlist. Só é possível baixar o vídeo, não a playlist inteira.";
        botaoUsarSoVideo.classList.remove("escondido");
        botaoUsarSoVideo.onclick = () => {
            campoUrl.value = analise.linkLimpo;
            aoMudarLink();
        };
    }
}

// ==========================================
// PRÉVIA DO VÍDEO
// ==========================================
const previa = document.getElementById("previa");
const previaMidia = document.getElementById("previa-midia");
const previaMiniatura = document.getElementById("previa-miniatura");
const previaPlay = document.getElementById("previa-play");
const previaDuracao = document.getElementById("previa-duracao");
const previaTitulo = document.getElementById("previa-titulo");
const previaCanal = document.getElementById("previa-canal");

let previaAtual = null; // { chave, id, titulo } do vídeo mostrado
let esperaDigitacao = null;
let consultaEmAndamento = null;

// Pega o ID do vídeo em links do YouTube (watch?v=, youtu.be/, shorts/...)
function idDoYoutube(texto) {
    try {
        const link = new URL(texto.trim());
        if (!/(^|\.)(youtube\.com|youtu\.be)$/.test(link.hostname)) return null;
        if (link.searchParams.get("v")) return link.searchParams.get("v");
        if (link.hostname.endsWith("youtu.be")) return link.pathname.slice(1) || null;
        const caminho = link.pathname.match(/^\/(shorts|live|embed)\/([^/?]+)/);
        return caminho ? caminho[2] : null;
    } catch {
        return null;
    }
}

function esconderPrevia() {
    previa.classList.add("escondido");
    previaAtual = null;
    campoFim.placeholder = "fim";
}

// Volta a mostrar a miniatura (tira o vídeo que estava tocando)
function mostrarMiniatura(endereco) {
    previa.classList.remove("assistindo");
    previaMidia.querySelector("iframe")?.remove();
    previaMiniatura.hidden = false;
    previaMiniatura.src = endereco || "";
}

function atualizarPrevia() {
    const texto = campoUrl.value.trim();
    const tipo = analisarLink(texto).tipo;
    if (!texto || tipo === "playlist") {
        esconderPrevia();
        return;
    }

    const id = idDoYoutube(texto);
    const chave = id || texto;
    if (previaAtual && previaAtual.chave === chave) return; // mesmo vídeo: mantém

    // Mostra na hora a miniatura (vem direto do YouTube) e busca o resto na API
    previaAtual = { chave, id, titulo: null };
    previa.classList.remove("escondido", "nao-encontrado");
    previa.classList.add("carregando");
    mostrarMiniatura(id ? `https://i.ytimg.com/vi/${id}/hqdefault.jpg` : "");
    previaPlay.hidden = !id;
    previaDuracao.textContent = "";
    previaTitulo.textContent = "Carregando prévia...";
    previaCanal.textContent = "";

    consultaEmAndamento?.abort();
    consultaEmAndamento = new AbortController();
    const consultaDestePedido = previaAtual;

    fetch(`/api/info?url=${encodeURIComponent(texto)}`, { signal: consultaEmAndamento.signal })
        .then(async (resposta) => {
            const dados = await resposta.json();
            if (previaAtual !== consultaDestePedido) return; // o link mudou nesse meio-tempo
            previa.classList.remove("carregando");

            if (!resposta.ok) {
                previa.classList.add("nao-encontrado");
                previaTitulo.textContent = dados.erro;
                return;
            }

            previaAtual.titulo = dados.titulo;
            previaTitulo.textContent = dados.titulo;
            previaCanal.textContent = dados.canal || "";
            previaDuracao.textContent = dados.duracao || "";
            campoFim.placeholder = dados.duracao || "fim"; // dica para o corte
            if (!id && dados.miniatura) mostrarMiniatura(dados.miniatura);
        })
        .catch(() => {});
}

// Clicar no play: o vídeo toca dentro do card
previaPlay.addEventListener("click", () => {
    if (!previaAtual?.id) return;
    const player = document.createElement("iframe");
    player.src = `https://www.youtube-nocookie.com/embed/${encodeURIComponent(previaAtual.id)}?autoplay=1`;
    player.allow = "autoplay; encrypted-media; picture-in-picture";
    player.allowFullscreen = true;
    previaMiniatura.hidden = true;
    previaMidia.appendChild(player);
    previa.classList.add("assistindo");
});

// Se a miniatura não existir, mostra o fundo vazio em vez de uma imagem quebrada
previaMiniatura.addEventListener("error", () => (previaMiniatura.hidden = true));

function aoMudarLink() {
    atualizarAvisoPlaylist();
    // Espera a pessoa parar de digitar antes de consultar a API
    clearTimeout(esperaDigitacao);
    esperaDigitacao = setTimeout(atualizarPrevia, 400);
}

campoUrl.addEventListener("input", aoMudarLink);

// ==========================================
// CORTAR TRECHO
// ==========================================
const botaoCortar = document.getElementById("botao-cortar");
const camposTrecho = document.getElementById("campos-trecho");
const campoInicio = document.getElementById("trecho-inicio");
const campoFim = document.getElementById("trecho-fim");
const erroTrecho = document.getElementById("erro-trecho");

botaoCortar.addEventListener("click", () => {
    const ativo = botaoCortar.classList.toggle("ativo");
    camposTrecho.classList.toggle("escondido", !ativo);
    if (ativo) {
        campoInicio.focus();
    } else {
        campoInicio.value = campoFim.value = "";
        mostrarErroTrecho("");
    }
});

// "1:20" -> 80 | "" -> null | texto inválido -> NaN
function lerTempo(texto) {
    texto = texto.trim();
    if (!texto) return null;
    const partes = texto.split(":");
    if (partes.length > 3 || partes.some((p) => !/^\d+(\.\d+)?$/.test(p))) return NaN;
    return partes.reduce((total, parte) => total * 60 + Number(parte), 0);
}

function mostrarErroTrecho(mensagem, campo) {
    erroTrecho.textContent = mensagem;
    [campoInicio, campoFim].forEach((c) => c.classList.toggle("invalido", c === campo));
}

[campoInicio, campoFim].forEach((campo) => campo.addEventListener("input", () => mostrarErroTrecho("")));

// Devolve { inicio, fim } (ou null se não for cortar); false se os tempos forem inválidos
function trechoEscolhido() {
    if (!botaoCortar.classList.contains("ativo")) return null;
    const inicio = lerTempo(campoInicio.value);
    const fim = lerTempo(campoFim.value);

    if (Number.isNaN(inicio)) return mostrarErroTrecho("Início inválido. Use minutos:segundos, ex.: 1:20", campoInicio), false;
    if (Number.isNaN(fim)) return mostrarErroTrecho("Fim inválido. Use minutos:segundos, ex.: 2:05", campoFim), false;
    if (inicio === null && fim === null) return null; // nada preenchido: baixa o vídeo inteiro
    if (fim !== null && fim <= (inicio || 0)) return mostrarErroTrecho("O fim precisa ser depois do início.", campoFim), false;

    return { inicio: campoInicio.value.trim() || "0:00", fim: campoFim.value.trim() || null };
}

// Envia o link para a fila
document.getElementById("form-download").addEventListener("submit", async (evento) => {
    evento.preventDefault();
    if (analisarLink(campoUrl.value).tipo !== "comum") return;

    const trecho = trechoEscolhido();
    if (trecho === false) return;

    const linkEnviado = campoUrl.value;
    const tituloEnviado = previaAtual?.titulo;
    const resposta = await fetch("/api/download", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ url: linkEnviado, formato: formatoEscolhido, qualidade: qualidadeEscolhida, ...trecho }),
    });
    const dados = await resposta.json();

    if (!resposta.ok) {
        alert(dados.erro);
        return;
    }

    let descricao = formatoEscolhido === "mp3" ? "MP3" : `MP4 ${qualidadeEscolhida}`;
    if (trecho) descricao += ` · trecho ${trecho.inicio} a ${trecho.fim || "fim"}`;
    criarItem(dados.id, descricao, tituloEnviado);
    // Só limpa o campo se a pessoa ainda não colou outro link enquanto o pedido ia
    if (campoUrl.value === linkEnviado) {
        campoUrl.value = "";
        aoMudarLink();
    }
});

// Cria um item na lista e acompanha o progresso dele
function criarItem(id, descricao, tituloDaPrevia) {
    const item = document.createElement("li");
    item.className = "item";
    item.innerHTML = `
        <div class="item-topo">
            <span class="item-titulo"></span>
            <span class="item-status">Na fila...</span>
        </div>
        <div class="barra"><div class="barra-preenchida"></div></div>
        <div class="item-acoes">
            <button type="button" class="item-botao cancelar">✕ Cancelar</button>
        </div>
    `;
    // textContent (e não innerHTML): o título vem do vídeo e pode ter qualquer caractere
    item.querySelector(".item-titulo").textContent = tituloDaPrevia ? `${tituloDaPrevia} (${descricao})` : descricao;
    document.getElementById("lista-downloads").prepend(item);

    const titulo = item.querySelector(".item-titulo");
    const status = item.querySelector(".item-status");
    const barra = item.querySelector(".barra-preenchida");
    const acoes = item.querySelector(".item-acoes");
    const botaoCancelar = item.querySelector(".cancelar");

    botaoCancelar.addEventListener("click", async () => {
        botaoCancelar.disabled = true;
        botaoCancelar.textContent = "Cancelando...";
        await fetch(`/api/cancelar/${id}`, { method: "POST" }).catch(() => {});
    });

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

            // O arquivo já foi salvo na pasta Downloads
            acoes.innerHTML = `<span>✓ Salvo em Downloads</span>
                <button type="button" class="item-botao">📂 Mostrar na pasta</button>`;
            acoes.querySelector("span").title = dados.arquivo;
            acoes.querySelector("button").addEventListener("click", () => {
                fetch(`/api/mostrar/${id}`, { method: "POST" })
                    .then((r) => (r.ok ? null : r.json().then((d) => alert(d.erro))))
                    .catch(() => {});
            });
        }

        if (dados.status === "Cancelado") {
            clearInterval(intervalo);
            item.classList.add("cancelado");
            acoes.innerHTML = "";
        }

        if (dados.status === "Erro" || dados.status === "Desconhecido") {
            clearInterval(intervalo);
            item.classList.add("erro");
            status.textContent = "Erro ao baixar";
            acoes.innerHTML = "";
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
