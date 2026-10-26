"""O que é comum aos sites suportados (YouTube, TikTok e Instagram)."""
import os

from servicos.caminhos import PASTA_BASE

# Login opcional: alguns posts do Instagram só abrem com uma conta logada.
# Coloque um cookies.txt (exportado do navegador com uma extensão como
# "Get cookies.txt LOCALLY") ao lado do programa e ele passa a ser usado.
ARQUIVO_COOKIES = os.path.join(PASTA_BASE, "cookies.txt")

NOMES_DOS_SITES = {"Youtube": "YouTube", "YoutubeTab": "YouTube", "TikTok": "TikTok", "Instagram": "Instagram"}


def opcoes_de_login():
    """Opções do yt-dlp para usar o login do cookies.txt, se ele existir."""
    if os.path.isfile(ARQUIVO_COOKIES):
        return {"cookiefile": ARQUIVO_COOKIES}
    return {}


def nome_do_site(info):
    return NOMES_DOS_SITES.get(info.get("extractor_key"), info.get("extractor_key") or "")


def titulo_amigavel(info):
    """O Instagram devolve títulos como "Video by fulano"; nesses casos usa a
    primeira linha da legenda do post, que descreve melhor o vídeo."""
    titulo = (info.get("title") or "").strip()
    autor = info.get("channel") or info.get("uploader") or ""
    if not titulo or titulo.lower().startswith(("video by ", "post by ")):
        legenda = (info.get("description") or "").strip().splitlines()
        primeira_linha = legenda[0].strip() if legenda else ""
        if primeira_linha:
            titulo = primeira_linha
        elif autor:
            titulo = f"Vídeo de {autor}"
    if len(titulo) > 100:
        titulo = titulo[:100].rstrip() + "…"
    return titulo or info.get("id") or "video"


def mensagem_de_erro(erro):
    """Traduz os erros mais comuns do yt-dlp para uma mensagem que o usuário entenda."""
    texto = str(erro).lower()
    if "empty media response" in texto:
        # O Instagram responde assim tanto para post apagado/privado quanto para post que pede login
        return ("Não foi possível abrir esse post do Instagram. Ele pode ser privado, ter sido apagado "
                "ou exigir login (nesse caso, veja no README como usar o arquivo cookies.txt).")
    if "login" in texto or "cookies" in texto or "rate-limit" in texto:
        return ("Esse post exige login para ser baixado. Coloque um arquivo cookies.txt "
                "ao lado do programa (veja o README) e tente de novo.")
    if "private" in texto or "privado" in texto:
        return "Esse vídeo é privado."
    if "unsupported url" in texto:
        return "Link não suportado. Use links do YouTube, TikTok ou Instagram."
    if "not available" in texto or "unavailable" in texto or "removed" in texto or "404" in texto:
        return "Esse vídeo não está disponível (pode ter sido apagado ou ser restrito)."
    return "Não encontramos esse vídeo. Confira o link."
