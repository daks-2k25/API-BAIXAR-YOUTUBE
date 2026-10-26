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
        // Cada aba mostra a seção com o mesmo id (youtube, heic, meus-downloads)
        document.querySelectorAll("main > section.card").forEach((secao) => {
            secao.classList.toggle("escondido", secao.id !== aba.dataset.aba);
        });
        if (aba.dataset.aba === "meus-downloads") carregarHistorico();
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
            // Ex.: "clinicavittace · Instagram"
            previaCanal.textContent = [dados.canal, dados.site].filter(Boolean).join(" · ");
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
            acoes.textContent = dados.erro || ""; // motivo (ex.: o post exige login)
        }
    }, 500);
}

// ==========================================
// FERRAMENTA 2: CONVERTER FOTO (HEIC -> JPG, HEIC/JPG/PNG -> WebP)
// ==========================================
const areaArquivo = document.getElementById("area-arquivo");
const campoArquivo = document.getElementById("arquivo-heic");
const textoArquivo = document.getElementById("texto-arquivo");
const statusHeic = document.getElementById("status-heic");

// Mesmas regras do servicos/conversor.py: JPG só a partir de HEIC (PNG transparente ficaria com fundo preto)
const ENTRADAS_POR_FORMATO = {
    jpg: { aceita: ".heic,.heif", texto: "<b>.heic</b>" },
    webp: { aceita: ".heic,.heif,.jpg,.jpeg,.png", texto: "<b>.heic</b>, <b>.jpg</b> ou <b>.png</b>" },
};
let formatoFoto = "jpg";

document.querySelectorAll("#formatos-foto .chip").forEach((chip) => {
    chip.addEventListener("click", () => {
        document.querySelectorAll("#formatos-foto .chip").forEach((c) => c.classList.remove("ativo"));
        chip.classList.add("ativo");
        formatoFoto = chip.dataset.formato;
        campoArquivo.accept = ENTRADAS_POR_FORMATO[formatoFoto].aceita;
        textoArquivo.innerHTML = `Clique ou arraste uma foto ${ENTRADAS_POR_FORMATO[formatoFoto].texto} aqui`;
        statusHeic.textContent = "";
    });
});

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
    formulario.append("formato", formatoFoto);

    // ?salvar=1: a foto vai direto para a pasta Downloads, igual aos vídeos
    const resposta = await fetch("/api/converter/imagem?salvar=1", { method: "POST", body: formulario });
    const dados = await resposta.json();

    if (!resposta.ok) {
        statusHeic.textContent = dados.erro;
        return;
    }

    statusHeic.innerHTML = `<span></span> <button type="button" class="item-botao">📂 Mostrar na pasta</button>`;
    statusHeic.querySelector("span").textContent = `✓ ${dados.arquivo} salvo em Downloads`;
    statusHeic.querySelector("button").addEventListener("click", () => {
        fetch(`/api/mostrar/${dados.id}`, { method: "POST" }).catch(() => {});
    });
    campoArquivo.value = "";
}

// ==========================================
// MEUS DOWNLOADS: histórico do que o programa salvou
// ==========================================
const listaHistorico = document.getElementById("lista-historico");
const historicoVazio = document.getElementById("historico-vazio");
const ICONES_HISTORICO = { video: "▶", musica: "♪", foto: "▣", outro: "•" };
let itensHistorico = [];
let filtroHistorico = "todos";

document.querySelectorAll("#filtros-historico .chip").forEach((chip) => {
    chip.addEventListener("click", () => {
        document.querySelectorAll("#filtros-historico .chip").forEach((c) => c.classList.remove("ativo"));
        chip.classList.add("ativo");
        filtroHistorico = chip.dataset.tipo;
        mostrarHistorico();
    });
});

document.getElementById("limpar-historico").addEventListener("click", async () => {
    if (!confirm("Limpar a lista? Os arquivos continuam na pasta Downloads.")) return;
    await fetch("/api/historico", { method: "DELETE" }).catch(() => {});
    carregarHistorico();
});

async function carregarHistorico() {
    try {
        itensHistorico = await (await fetch("/api/historico")).json();
    } catch {
        itensHistorico = [];
    }
    mostrarHistorico();
}

// 35651584 -> "34 MB"
function formatarTamanho(bytes) {
    if (bytes == null) return "";
    const unidades = ["B", "KB", "MB", "GB"];
    let valor = bytes;
    let i = 0;
    while (valor >= 1024 && i < unidades.length - 1) {
        valor /= 1024;
        i++;
    }
    return `${valor.toLocaleString("pt-BR", { maximumFractionDigits: valor < 10 && i > 1 ? 1 : 0 })} ${unidades[i]}`;
}

function formatarData(segundos) {
    return new Date(segundos * 1000).toLocaleString("pt-BR", {
        day: "2-digit", month: "short", year: "numeric", hour: "2-digit", minute: "2-digit",
    });
}

function mostrarHistorico() {
    const itens = itensHistorico.filter((i) => filtroHistorico === "todos" || i.tipo === filtroHistorico);
    listaHistorico.replaceChildren();
    document.getElementById("limpar-historico").hidden = itensHistorico.length === 0;

    historicoVazio.classList.toggle("escondido", itens.length > 0);
    historicoVazio.textContent = itensHistorico.length === 0
        ? "Nada por aqui ainda. Os vídeos, músicas e fotos que você salvar pelo programa aparecem nesta aba."
        : "Nenhum arquivo desse tipo na lista.";

    itens.forEach((dados) => {
        const item = document.createElement("li");
        item.className = "item historico-item" + (dados.existe ? "" : " ausente");
        item.innerHTML = `
            <div class="historico-linha">
                <span class="historico-icone"></span>
                <div class="historico-info">
                    <span class="item-titulo"></span>
                    <span class="historico-detalhes"></span>
                </div>
            </div>
            <div class="item-acoes"></div>
        `;
        // textContent (e não innerHTML): o título vem do vídeo e pode ter qualquer caractere
        item.querySelector(".historico-icone").textContent = ICONES_HISTORICO[dados.tipo] || ICONES_HISTORICO.outro;
        const titulo = item.querySelector(".item-titulo");
        titulo.textContent = dados.titulo;
        titulo.title = dados.arquivo;
        item.querySelector(".historico-detalhes").textContent = dados.existe
            ? [dados.formato, formatarData(dados.data), formatarTamanho(dados.tamanho)].join(" · ")
            : `${dados.formato} · ${formatarData(dados.data)} · arquivo não encontrado (movido ou apagado)`;

        const acoes = item.querySelector(".item-acoes");
        const acao = (texto, aoClicar, classe = "") => {
            const botao = document.createElement("button");
            botao.type = "button";
            botao.className = `item-botao ${classe}`.trim();
            botao.textContent = texto;
            botao.addEventListener("click", aoClicar);
            acoes.appendChild(botao);
        };
        const chamar = (rota) => fetch(rota, { method: "POST" })
            .then((r) => (r.ok ? null : r.json().then((d) => { alert(d.erro); carregarHistorico(); })))
            .catch(() => {});

        if (dados.existe) {
            acao("▶ Abrir", () => chamar(`/api/abrir/${dados.id}`));
            acao("📂 Mostrar na pasta", () => chamar(`/api/mostrar/${dados.id}`));
        }
        acao("✕ Remover da lista", async () => {
            await fetch(`/api/historico/${dados.id}`, { method: "DELETE" }).catch(() => {});
            carregarHistorico();
        }, "remover");

        listaHistorico.appendChild(item);
    });
}

// ==========================================
// PROGRAMA: manter aberto / encerrar
// ==========================================

// Na janela própria do programa, fechar a janela já encerra tudo: o botão
// "Encerrar" some. No navegador, o painel avisa a cada 30 segundos que continua
// aberto; sem esse aviso por 3 minutos (e sem downloads), o programa fecha sozinho.
function avisarQuePainelEstaAberto() {
    fetch("/api/ping", { method: "POST" }).catch(() => {});
}

// ==========================================
// CONFIGURAÇÕES: abrir na janela do aplicativo ou no navegador
// ==========================================
const botaoConfig = document.getElementById("config");
const painelConfig = document.getElementById("configuracoes");
const botaoAbrirNavegador = document.getElementById("abrir-navegador");
const botaoTrocarAgora = document.getElementById("config-trocar");
const dicaConfig = document.getElementById("config-dica");
let modoAtual = { janela: false, preferencia: "janela" };

fetch("/api/modo")
    .then((r) => r.json())
    .then((modo) => {
        modoAtual = modo;
        if (modo.janela) {
            document.getElementById("encerrar").hidden = true;
            botaoAbrirNavegador.hidden = false; // atalho ↗ só faz sentido na janela
        } else {
            avisarQuePainelEstaAberto();
            setInterval(avisarQuePainelEstaAberto, 30000);
        }
        montarConfiguracoes();
    })
    .catch(() => {});

function montarConfiguracoes() {
    document.querySelectorAll("#config-modo .chip").forEach((chip) => {
        chip.classList.toggle("ativo", chip.dataset.modo === modoAtual.preferencia);
    });
    botaoTrocarAgora.textContent = modoAtual.janela ? "↗ Abrir no navegador agora" : "Reabrir como aplicativo";
}

botaoConfig.addEventListener("click", (evento) => {
    evento.stopPropagation();
    const abrir = painelConfig.classList.contains("escondido");
    painelConfig.classList.toggle("escondido", !abrir);
    botaoConfig.classList.toggle("aberto", abrir);
    painelNotificacoes.classList.add("escondido");
    sino.classList.remove("aberto");
    dicaConfig.textContent = "";
});

// Escolher como o programa abre (vale a partir da próxima vez)
document.querySelectorAll("#config-modo .chip").forEach((chip) => {
    chip.addEventListener("click", async () => {
        const resposta = await fetch("/api/preferencias", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ modo_abertura: chip.dataset.modo }),
        }).catch(() => null);
        if (!resposta || !resposta.ok) {
            dicaConfig.textContent = "Não foi possível salvar. Tente de novo.";
            return;
        }
        modoAtual.preferencia = chip.dataset.modo;
        montarConfiguracoes();
        dicaConfig.textContent = chip.dataset.modo === "navegador"
            ? "✓ Salvo. Das próximas vezes, o programa abre no navegador."
            : "✓ Salvo. Das próximas vezes, o programa abre na janela do aplicativo.";
    });
});

async function abrirNoNavegadorAgora() {
    // A janela fecha e o painel abre no navegador; o programa continua rodando
    await fetch("/api/abrir-no-navegador", { method: "POST" }).catch(() => {});
}

async function reabrirComoAplicativo() {
    await fetch("/api/reabrir-como-aplicativo", { method: "POST" }).catch(() => {});
    document.body.innerHTML = `
        <div class="brilho"></div>
        <div class="encerrado">
            <h1>Abrindo como aplicativo...</h1>
            <p>A janela do programa vai abrir em alguns segundos.</p>
        </div>
    `;
    const mensagem = document.querySelector(".encerrado p");

    // Espera o programa fechar e voltar já como aplicativo; aí fecha esta aba
    // sozinha. O navegador só deixa fechar a aba que o programa abriu (sem
    // outras páginas no histórico); se não deixar, fica o aviso para fechar.
    const pausa = (ms) => new Promise((pronto) => setTimeout(pronto, ms));
    const inicio = Date.now();
    let caiu = false;
    let voltouEm = null;

    while (Date.now() - inicio < 30000) {
        await pausa(700);
        try {
            const modo = await (await fetch("/api/modo", { cache: "no-store" })).json();
            if (!caiu) continue; // ainda é o programa antigo, fechando
            voltouEm ??= Date.now();
            // O servidor volta um instante antes de a janela existir: espera ela
            // aparecer (se não aparecer, o programa abriu no navegador)
            if (!modo.janela && Date.now() - voltouEm < 8000) continue;

            document.querySelector(".encerrado h1").textContent = "Pronto!";
            mensagem.textContent = modo.janela
                ? "O aplicativo foi aberto. Pode fechar esta aba."
                : "O painel abriu em outra aba. Pode fechar esta.";
            window.close();
            return;
        } catch {
            caiu = true;
        }
    }
    mensagem.textContent = "O aplicativo não abriu. Abra pelo atalho Baixar YouTube na Área de Trabalho.";
}

botaoAbrirNavegador.addEventListener("click", abrirNoNavegadorAgora);
botaoTrocarAgora.addEventListener("click", () =>
    modoAtual.janela ? abrirNoNavegadorAgora() : reabrirComoAplicativo()
);

document.getElementById("encerrar").addEventListener("click", async () => {
    if (!confirm("Encerrar o programa? Downloads em andamento serão interrompidos.")) return;

    await fetch("/api/encerrar", { method: "POST" }).catch(() => {});
    document.body.innerHTML = `
        <div class="brilho"></div>
        <div class="encerrado">
            <h1>Programa encerrado</h1>
            <p>Pode fechar esta aba. Para usar de novo, abra o atalho Baixar YouTube.</p>
        </div>
    `;
});

// ==========================================
// ATUALIZAÇÃO DO PROGRAMA E NOTIFICAÇÕES
// ==========================================
const avisoAtualizacao = document.getElementById("aviso-atualizacao");
const botaoAtualizar = document.getElementById("botao-atualizar");
const botaoDepois = document.getElementById("botao-depois");
const mensagemAtualizacao = document.getElementById("atualizacao-mensagem");
const sino = document.getElementById("sino");
const sinoPonto = document.getElementById("sino-ponto");
const painelNotificacoes = document.getElementById("notificacoes");
const conteudoNotificacoes = document.getElementById("notificacoes-conteudo");
const toast = document.getElementById("toast");

// Com o programa aberto, confere se saiu versão nova a cada 30 minutos
const VERIFICAR_A_CADA = 30 * 60 * 1000;

let infoVersao = null;
let toastMostradoPara = null; // a notificação aparece uma vez por versão
let atualizando = false;

async function verificarAtualizacao(forcar = false) {
    try {
        infoVersao = await (await fetch(`/api/versao${forcar ? "?forcar=1" : ""}`)).json();
    } catch {
        return;
    }
    mostrarVersao();
}

function mostrarVersao() {
    const dados = infoVersao;
    document.getElementById("versao").textContent = `Versão ${dados.atual}`;
    sinoPonto.hidden = !dados.disponivel;
    montarPainelNotificacoes();
    if (!dados.disponivel || atualizando) return;

    // Aviso no topo do painel
    document.getElementById("atualizacao-titulo").textContent = `✨ Nova versão ${dados.nova} disponível`;
    preencherNovidades(document.getElementById("atualizacao-novidades"), dados.novidades);
    botaoAtualizar.hidden = !dados.pode_atualizar;
    mensagemAtualizacao.textContent = dados.pode_atualizar ? "" : dados.motivo;

    // "Depois": o aviso e a notificação somem; o sino continua com a bolinha
    if (dados.adiada) {
        avisoAtualizacao.classList.add("escondido");
        return;
    }
    avisoAtualizacao.classList.remove("escondido");

    if (toastMostradoPara !== dados.nova) {
        toastMostradoPara = dados.nova;
        document.getElementById("toast-titulo").textContent = `✨ Nova versão ${dados.nova} disponível`;
        const primeira = dados.novidades[0];
        document.getElementById("toast-descricao").textContent = primeira
            ? primeira + (dados.novidades.length > 1 ? " e mais novidades." : "")
            : "";
        document.getElementById("toast-atualizar").hidden = !dados.pode_atualizar;
        toast.classList.remove("escondido");
    }
}

function preencherNovidades(lista, novidades) {
    lista.innerHTML = "";
    novidades.forEach((novidade) => {
        const item = document.createElement("li");
        item.textContent = novidade; // textContent: o texto vem de fora
        lista.appendChild(item);
    });
}

// Conteúdo do painelzinho que abre no sino
function montarPainelNotificacoes() {
    const dados = infoVersao;
    conteudoNotificacoes.innerHTML = "";
    const item = document.createElement("div");
    item.className = "notificacao-item";

    if (dados.disponivel) {
        item.innerHTML = `<strong></strong><ul></ul><div class="atualizacao-botoes"></div>`;
        item.querySelector("strong").textContent = `✨ Nova versão ${dados.nova} disponível`;
        preencherNovidades(item.querySelector("ul"), dados.novidades);
        if (dados.pode_atualizar) {
            const botao = document.createElement("button");
            botao.type = "button";
            botao.className = "botao-atualizar";
            botao.textContent = "⬆ Atualizar agora";
            botao.addEventListener("click", iniciarAtualizacao);
            item.querySelector(".atualizacao-botoes").appendChild(botao);
        } else {
            const motivo = document.createElement("p");
            motivo.textContent = dados.motivo;
            item.appendChild(motivo);
        }
    } else {
        item.innerHTML = `<p></p><button type="button" class="botao-depois">↻ Verificar agora</button>`;
        item.querySelector("p").textContent = dados.motivo || `✓ Você está na versão mais recente (${dados.atual}).`;
        const botaoVerificar = item.querySelector("button");
        botaoVerificar.addEventListener("click", async () => {
            botaoVerificar.disabled = true;
            botaoVerificar.textContent = "Verificando...";
            await verificarAtualizacao(true);
        });
    }
    conteudoNotificacoes.appendChild(item);
}

sino.addEventListener("click", (evento) => {
    evento.stopPropagation();
    const abrir = painelNotificacoes.classList.contains("escondido");
    painelNotificacoes.classList.toggle("escondido", !abrir);
    sino.classList.toggle("aberto", abrir);
    if (abrir) toast.classList.add("escondido");
    painelConfig.classList.add("escondido");
    botaoConfig.classList.remove("aberto");
});

// Clicar fora fecha os painelzinhos (notificações e configurações)
document.addEventListener("click", (evento) => {
    if (!painelNotificacoes.contains(evento.target)) {
        painelNotificacoes.classList.add("escondido");
        sino.classList.remove("aberto");
    }
    if (!painelConfig.contains(evento.target)) {
        painelConfig.classList.add("escondido");
        botaoConfig.classList.remove("aberto");
    }
});

async function adiarAtualizacao() {
    toast.classList.add("escondido");
    avisoAtualizacao.classList.add("escondido");
    if (!infoVersao || !infoVersao.nova) return;
    infoVersao.adiada = true;
    await fetch("/api/versao/adiar", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ versao: infoVersao.nova }),
    }).catch(() => {});
}

botaoDepois.addEventListener("click", adiarAtualizacao);
document.getElementById("toast-depois").addEventListener("click", adiarAtualizacao);
document.getElementById("toast-atualizar").addEventListener("click", iniciarAtualizacao);
botaoAtualizar.addEventListener("click", iniciarAtualizacao);

async function iniciarAtualizacao() {
    if (atualizando) return;
    atualizando = true;

    // O andamento aparece no aviso do topo
    toast.classList.add("escondido");
    painelNotificacoes.classList.add("escondido");
    avisoAtualizacao.classList.remove("escondido");
    avisoAtualizacao.scrollIntoView({ behavior: "smooth", block: "start" });
    botaoDepois.hidden = true;
    botaoAtualizar.hidden = false;
    botaoAtualizar.disabled = true;
    botaoAtualizar.textContent = "Atualizando...";
    mensagemAtualizacao.textContent = "Baixando a versão nova. Não feche o programa.";

    const resposta = await fetch("/api/atualizar", { method: "POST" }).catch(() => null);
    const dados = resposta ? await resposta.json().catch(() => ({})) : {};

    if (!resposta || !resposta.ok) {
        atualizando = false;
        mensagemAtualizacao.textContent = dados.erro || "Não foi possível atualizar. Tente de novo.";
        botaoAtualizar.disabled = false;
        botaoAtualizar.textContent = "⬆ Tentar de novo";
        botaoDepois.hidden = false;
        return;
    }

    botaoAtualizar.hidden = true;
    mensagemAtualizacao.textContent = `✓ Atualizado para a versão ${dados.versao}. Reiniciando o programa...`;

    // No navegador: espera o programa voltar e recarrega a página.
    // Na janela própria, ela fecha e abre de novo sozinha.
    let caiu = false;
    const esperar = setInterval(async () => {
        try {
            await fetch("/api/modo", { cache: "no-store" });
            if (caiu) {
                clearInterval(esperar);
                location.reload();
            }
        } catch {
            caiu = true;
        }
    }, 1000);
}

carregarQualidades();
verificarAtualizacao();
setInterval(() => verificarAtualizacao(), VERIFICAR_A_CADA);
