"""O que as rotas têm em comum: arquivos enviados, salvar em Downloads e enviar de volta."""
import os
import shutil

from werkzeug.wsgi import ClosingIterator

from servicos import destinos, historico
from servicos.caminhos import PASTA_DOWNLOADS
from servicos.downloader import arquivos_salvos, caminho_sem_sobrescrever, nome_de_arquivo_seguro


def ao_terminar_envio(resposta, funcao):
    """Executa a função só depois que o arquivo foi enviado e fechado.
    (No Windows não dá para apagar um arquivo que ainda está aberto.)"""
    resposta.response = ClosingIterator(resposta.response, funcao)
    return resposta


def extensao_do_arquivo(nome):
    """"Foto.HEIC" -> "heic". Sem extensão -> ""."""
    return nome.rsplit('.', 1)[-1].lower() if '.' in nome else ''


def nome_sem_extensao(nome):
    return nome.rsplit('.', 1)[0]


def guardar_enviado(arquivo, id_arquivo, extensao):
    """Salva o arquivo enviado pelo painel na pasta temporária (com a extensão
    original, que o FFmpeg usa) e devolve o caminho."""
    caminho = os.path.join(PASTA_DOWNLOADS, f"{id_arquivo}_original.{extensao}")
    arquivo.save(caminho)
    return caminho


def apagar(*caminhos):
    for caminho in caminhos:
        if caminho and os.path.exists(caminho):
            os.remove(caminho)


def salvar_no_destino(caminho, nome, formato, id_arquivo):
    """Move a foto pronta para a pasta de fotos escolhida em Configurações
    (Downloads, se nenhuma), sem sobrescrever outro arquivo, e a registra para
    "Mostrar na pasta" e "Meus downloads". Devolve o destino."""
    destino = caminho_sem_sobrescrever(destinos.pasta_para("foto"), nome_de_arquivo_seguro(nome), formato)
    shutil.move(caminho, destino)
    arquivos_salvos[id_arquivo] = destino
    historico.registrar(id_arquivo, destino, nome)
    return destino


def pasta_do_arquivo(caminho):
    """Nome da pasta onde o arquivo ficou, para o painel ("✓ Salvo em Músicas")."""
    return os.path.basename(os.path.dirname(caminho)) if caminho else None


def caminho_do_arquivo(id_arquivo):
    """Arquivo salvo nesta sessão ou, depois de reabrir o programa, pelo histórico."""
    return arquivos_salvos.get(id_arquivo) or historico.caminho(id_arquivo)
