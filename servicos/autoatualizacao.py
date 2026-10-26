"""Atualiza o próprio programa pelo botão "Atualizar agora" do painel.

A versão instalada fica em versao.json. O painel compara com o versao.json do
GitHub e, se houver versão nova, oferece a atualização:

- Pasta baixada como ZIP: baixa o ZIP novo do GitHub e substitui os arquivos
  do projeto (downloads, ambiente, logs e atalho não são tocados).
- Pasta clonada com git: roda "git pull", mas só se estiver na branch principal
  e sem mudanças locais (para não atrapalhar quem está desenvolvendo).
- Programa gerado (BaixarYouTube.exe): o código está empacotado dentro dele;
  é preciso gerar o programa de novo.

Depois de atualizar, o programa reinicia pelo iniciar.bat, que também instala
bibliotecas novas, se a versão nova precisar.
"""
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.request
import zipfile

from servicos import preferencias
from servicos.caminhos import EXECUTAVEL, PASTA_RECURSOS

REPOSITORIO = "daks-2k25/API-BAIXAR-YOUTUBE"
RAMO = "main"
URL_VERSAO = f"https://raw.githubusercontent.com/{REPOSITORIO}/{RAMO}/versao.json"
URL_ZIP = f"https://codeload.github.com/{REPOSITORIO}/zip/refs/heads/{RAMO}"

PASTA_PROJETO = PASTA_RECURSOS
ARQUIVO_VERSAO = os.path.join(PASTA_PROJETO, "versao.json")
# Lista dos arquivos que vieram na última atualização (para apagar os que saírem do projeto)
ARQUIVO_MANIFESTO = os.path.join(PASTA_PROJETO, ".arquivos_do_programa.txt")

# Pastas e arquivos da pessoa que a atualização nunca toca
PROTEGIDOS = (
    ".git", ".ambiente", ".venv", "downloads", "BaixarYouTube", "atualizacoes",
    "ferramentas/compilacao", ".atalho_criado", ".arquivos_do_programa.txt",
    ".preferencias.json", "cookies.txt",
)


# Guarda a última consulta ao GitHub por alguns minutos
_cache = {"momento": 0, "dados": None}
CACHE_SEGUNDOS = 10 * 60


def _versao_como_tupla(versao):
    return tuple(int(p) for p in str(versao).split(".") if p.isdigit())


def versao_instalada():
    try:
        with open(ARQUIVO_VERSAO, encoding="utf-8") as f:
            return json.load(f).get("versao", "0")
    except (OSError, ValueError):
        return "0"


def versao_adiada():
    """Versão nova que a pessoa mandou avisar depois (não mostra a notificação de novo)."""
    return preferencias.obter("atualizacao_adiada")


def adiar(versao):
    preferencias.salvar("atualizacao_adiada", str(versao))


def _git(*argumentos):
    resultado = subprocess.run(
        ["git", *argumentos], cwd=PASTA_PROJETO, capture_output=True, text=True,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )
    return resultado.returncode, (resultado.stdout + resultado.stderr).strip()


def como_atualizar():
    """Devolve ("zip" | "git", None) ou (None, motivo pelo qual não dá para atualizar aqui)."""
    if EXECUTAVEL:
        return None, "Este é o programa gerado (BaixarYouTube.exe): para atualizar, gere o programa de novo com ferramentas\\gerar_exe.bat."

    if os.path.isdir(os.path.join(PASTA_PROJETO, ".git")):
        if shutil.which("git") is None:
            return None, "Esta pasta usa git, mas o git não foi encontrado. Atualize com \"git pull\"."
        codigo, ramo = _git("rev-parse", "--abbrev-ref", "HEAD")
        if codigo != 0 or ramo != RAMO:
            return None, f"Esta pasta está na branch \"{ramo}\". A atualização automática só funciona na branch \"{RAMO}\"."
        codigo, mudancas = _git("status", "--porcelain", "--untracked-files=no")
        if mudancas:
            return None, "Esta pasta tem alterações no código que ainda não foram salvas no git. Atualize com \"git pull\"."
        return "git", None

    return "zip", None


def verificar(forcar=False):
    """Compara a versão instalada com a do GitHub."""
    agora = time.time()
    if not forcar and _cache["dados"] and agora - _cache["momento"] < CACHE_SEGUNDOS:
        return _cache["dados"]

    atual = versao_instalada()
    dados = {"atual": atual, "nova": None, "novidades": [], "disponivel": False,
             "pode_atualizar": False, "motivo": None}
    try:
        pedido = urllib.request.Request(URL_VERSAO, headers={"Cache-Control": "no-cache"})
        with urllib.request.urlopen(pedido, timeout=8) as resposta:
            remoto = json.load(resposta)
        dados["nova"] = remoto.get("versao")
        dados["novidades"] = remoto.get("novidades", [])
        dados["disponivel"] = _versao_como_tupla(dados["nova"]) > _versao_como_tupla(atual)
    except Exception as e:
        dados["motivo"] = f"Não foi possível verificar atualizações ({e})."
        return dados  # sem cache: tenta de novo na próxima vez

    if dados["disponivel"]:
        forma, motivo = como_atualizar()
        dados["pode_atualizar"] = forma is not None
        dados["motivo"] = motivo

    _cache.update(momento=agora, dados=dados)
    return dados


def _protegido(caminho_relativo):
    caminho = caminho_relativo.replace("\\", "/")
    return caminho.endswith(".log") or any(
        caminho == p or caminho.startswith(p + "/") for p in PROTEGIDOS
    )


def _atualizar_pelo_zip():
    with urllib.request.urlopen(URL_ZIP, timeout=60) as resposta:
        conteudo = resposta.read()

    with zipfile.ZipFile(io.BytesIO(conteudo)) as pacote:
        # O ZIP do GitHub tem tudo dentro de uma pasta "REPOSITORIO-RAMO/"
        raiz = pacote.namelist()[0].split("/")[0] + "/"
        arquivos = {
            nome[len(raiz):]: nome for nome in pacote.namelist()
            if nome.startswith(raiz) and not nome.endswith("/") and nome != raiz
        }
        if "app.py" not in arquivos or "versao.json" not in arquivos:
            raise ValueError("o pacote baixado não parece ser deste programa")

        # Extrai tudo numa pasta temporária primeiro: se algo falhar no meio,
        # o programa instalado continua intacto
        with tempfile.TemporaryDirectory() as temporaria:
            for relativo, nome in arquivos.items():
                if _protegido(relativo):
                    continue
                destino_temporario = os.path.join(temporaria, relativo)
                os.makedirs(os.path.dirname(destino_temporario), exist_ok=True)
                with pacote.open(nome) as origem, open(destino_temporario, "wb") as destino:
                    shutil.copyfileobj(origem, destino)

            # Copia por cima dos arquivos do projeto
            novos = set()
            for pasta, _, nomes in os.walk(temporaria):
                for nome in nomes:
                    origem = os.path.join(pasta, nome)
                    relativo = os.path.relpath(origem, temporaria).replace("\\", "/")
                    destino = os.path.join(PASTA_PROJETO, relativo)
                    os.makedirs(os.path.dirname(destino), exist_ok=True)
                    shutil.copy2(origem, destino)
                    novos.add(relativo)

    # Apaga arquivos que existiam na versão anterior e saíram do projeto
    try:
        with open(ARQUIVO_MANIFESTO, encoding="utf-8") as f:
            antigos = {linha.strip() for linha in f if linha.strip()}
    except OSError:
        antigos = set()  # primeira atualização: não apaga nada
    for relativo in antigos - novos:
        caminho = os.path.join(PASTA_PROJETO, relativo)
        if not _protegido(relativo) and os.path.isfile(caminho):
            os.remove(caminho)

    with open(ARQUIVO_MANIFESTO, "w", encoding="utf-8") as f:
        f.write("\n".join(sorted(novos)))


def _atualizar_pelo_git():
    codigo, saida = _git("pull", "--ff-only", "origin", RAMO)
    if codigo != 0:
        raise RuntimeError(f"git pull falhou: {saida}")


def aplicar():
    """Baixa e instala a versão nova. Não reinicia (veja reiniciar())."""
    forma, motivo = como_atualizar()
    if forma is None:
        raise RuntimeError(motivo)
    print(f"[ATUALIZAÇÃO] Atualizando pelo {forma} (versão atual: {versao_instalada()})...")
    if forma == "git":
        _atualizar_pelo_git()
    else:
        _atualizar_pelo_zip()
    _cache.update(momento=0, dados=None)
    print(f"[ATUALIZAÇÃO] Atualizado para a versão {versao_instalada()}.")


def reiniciar():
    """Abre o iniciar.bat daqui a 2 segundos (tempo de este processo fechar).
    O iniciar.bat instala bibliotecas novas, se houver, e abre o programa de novo."""
    iniciar = os.path.join(PASTA_PROJETO, "iniciar.bat")
    sem_janela = getattr(subprocess, "CREATE_NO_WINDOW", 0) | getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
    # "ping" para esperar: o "timeout" do Windows falha quando não há janela de console
    subprocess.Popen(
        f'cmd /c ping -n 3 127.0.0.1 >nul & "{iniciar}"',
        cwd=PASTA_PROJETO, creationflags=sem_janela, close_fds=True,
    )
