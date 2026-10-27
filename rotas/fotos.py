"""Fotos: converter (HEIC -> JPG, HEIC/JPG/PNG -> WebP) e comprimir.

As duas rotas recebem a foto como multipart/form-data no campo "arquivo".
Com ?salvar=1 (usado pelo painel), o resultado vai para a pasta Downloads e a
resposta é um JSON; sem ele, a resposta é a própria foto.
"""
import os
import uuid

from flask import Blueprint, jsonify, request, send_file

from rotas.utilidades import (
    ao_terminar_envio, apagar, extensao_do_arquivo, guardar_enviado, nome_sem_extensao, pasta_do_arquivo,
    salvar_no_destino,
)
from servicos import compressor
from servicos.caminhos import PASTA_DOWNLOADS
from servicos.conversor import FORMATOS, converter_imagem

rotas = Blueprint("fotos", __name__)


def foto_enviada():
    """A foto do form-data, ou (None, resposta de erro)."""
    arquivo = request.files.get('arquivo')
    if arquivo is None:
        return None, (jsonify({"erro": "Nenhum arquivo enviado. Use o campo 'arquivo' no form-data."}), 400)
    if arquivo.filename == '':
        return None, (jsonify({"erro": "Nenhum arquivo selecionado."}), 400)
    return arquivo, None


# /api/converter/heic é o endereço antigo (sempre JPG); continua funcionando
@rotas.route('/api/converter/heic', methods=['POST'])
@rotas.route('/api/converter/imagem', methods=['POST'])
def converter_imagem_api():
    arquivo, erro = foto_enviada()
    if erro:
        return erro

    formato = (request.form.get('formato') or request.args.get('formato') or 'jpg').lower()
    if formato not in FORMATOS:
        return jsonify({"erro": f"Formato inválido. Use: {', '.join(FORMATOS)}."}), 400

    extensao = extensao_do_arquivo(arquivo.filename)
    if extensao not in FORMATOS[formato]:
        aceitos = ", ".join(e.upper() for e in FORMATOS[formato])
        return jsonify({"erro": f"Para {formato.upper()}, envie uma foto {aceitos}."}), 400

    id_conversao = str(uuid.uuid4())
    caminho_original = guardar_enviado(arquivo, id_conversao, extensao)
    caminho_convertido = converter_imagem(
        caminho_original, formato, os.path.join(PASTA_DOWNLOADS, f"{id_conversao}.{formato}"),
    )

    if not caminho_convertido or not os.path.exists(caminho_convertido):
        apagar(caminho_original)
        return jsonify({"erro": f"Falha na conversão. Verifique se o arquivo é uma foto {extensao.upper()} válida."}), 500

    nome = nome_sem_extensao(arquivo.filename)

    if request.args.get('salvar') == '1':
        destino = salvar_no_destino(caminho_convertido, nome, formato, id_conversao)
        apagar(caminho_original)
        return jsonify({"id": id_conversao, "arquivo": os.path.basename(destino), "pasta": pasta_do_arquivo(destino)})

    resposta = send_file(caminho_convertido, as_attachment=True, download_name=f"{nome}.{formato}")
    return ao_terminar_envio(resposta, lambda: apagar(caminho_original, caminho_convertido))


@rotas.route('/api/comprimir', methods=['POST'])
def comprimir_api():
    arquivo, erro = foto_enviada()
    if erro:
        return erro

    extensao = extensao_do_arquivo(arquivo.filename)
    if extensao not in compressor.SAIDAS:
        return jsonify({"erro": "Envie uma foto JPG, PNG, WebP ou HEIC."}), 400

    nivel = request.form.get('nivel', compressor.NIVEL_PADRAO)
    tamanho = request.form.get('tamanho', 'original')
    if nivel not in compressor.NIVEIS or tamanho not in compressor.TAMANHOS:
        return jsonify({"erro": "Nível ou tamanho inválido."}), 400

    id_compressao = str(uuid.uuid4())
    caminho_original = guardar_enviado(arquivo, id_compressao, extensao)
    try:
        resultado = compressor.comprimir(
            caminho_original, extensao, nivel, compressor.TAMANHOS[tamanho], PASTA_DOWNLOADS,
        )
    except Exception as e:
        print(f"[COMPRESSOR] Erro ao comprimir {arquivo.filename}: {e}")
        return jsonify({"erro": "Não foi possível comprimir. Verifique se o arquivo é uma foto válida."}), 500
    finally:
        apagar(caminho_original)

    dados = {
        "id": id_compressao,
        "antes": resultado["antes"],
        "depois": resultado["depois"],
        "largura": resultado["largura"],
        "altura": resultado["altura"],
        "ja_otimizada": resultado["ja_otimizada"],
        "arquivo": None,
    }
    if resultado["ja_otimizada"]:
        return jsonify(dados)  # nada a salvar: a foto já estava bem comprimida

    nome = nome_sem_extensao(arquivo.filename)
    formato = resultado["formato"]

    if request.args.get('salvar') == '1':
        destino = salvar_no_destino(resultado["caminho"], f"{nome} (comprimida)", formato, id_compressao)
        dados["arquivo"] = os.path.basename(destino)
        dados["pasta"] = pasta_do_arquivo(destino)
        return jsonify(dados)

    caminho = resultado["caminho"]
    resposta = send_file(caminho, as_attachment=True, download_name=f"{nome}.{formato}")
    return ao_terminar_envio(resposta, lambda: apagar(caminho))
