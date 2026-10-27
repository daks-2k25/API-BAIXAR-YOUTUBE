"""Comprimir vídeos do computador (MP4, MOV, MKV...) para MP4 menor.

O vídeo é enviado como multipart/form-data no campo "arquivo" e entra numa
fila (um por vez). O andamento é acompanhado como o de um download:
/api/progresso e /api/cancelar.
"""
import uuid

from flask import Blueprint, jsonify, request

from rotas.utilidades import extensao_do_arquivo, guardar_enviado, nome_sem_extensao
from servicos import compressor_video as cv

rotas = Blueprint("comprimir_video", __name__)


@rotas.route('/api/comprimir-video', methods=['POST'])
def comprimir_video_api():
    arquivo = request.files.get('arquivo')
    if arquivo is None or arquivo.filename == '':
        return jsonify({"erro": "Nenhum arquivo enviado. Use o campo 'arquivo' no form-data."}), 400

    extensao = extensao_do_arquivo(arquivo.filename)
    if extensao not in cv.ENTRADAS:
        return jsonify({"erro": "Envie um vídeo (MP4, MOV, MKV, WebM, AVI...)."}), 400

    modo = request.form.get('modo', 'tamanho')
    resolucao = request.form.get('resolucao', 'original')
    if modo not in ('tamanho', 'qualidade') or resolucao not in cv.RESOLUCOES:
        return jsonify({"erro": "Modo ou resolução inválidos."}), 400

    tamanho_mb = qualidade = None
    if modo == 'tamanho':
        # "whatsapp", "discord", "email" ou um número de MB
        tamanho = request.form.get('tamanho', 'whatsapp')
        try:
            tamanho_mb = cv.TAMANHOS.get(tamanho) or float(tamanho.replace(',', '.'))
        except ValueError:
            tamanho_mb = None
        if not tamanho_mb or not cv.TAMANHO_MINIMO <= tamanho_mb <= cv.TAMANHO_MAXIMO:
            return jsonify({"erro": f"Tamanho inválido: use de {cv.TAMANHO_MINIMO} a {cv.TAMANHO_MAXIMO} MB."}), 400
        tamanho_mb = round(tamanho_mb, 1) if tamanho_mb % 1 else int(tamanho_mb)
    else:
        qualidade = request.form.get('qualidade', 'equilibrada')
        if qualidade not in cv.QUALIDADES:
            return jsonify({"erro": "Qualidade inválida."}), 400

    id_trabalho = str(uuid.uuid4())
    entrada = guardar_enviado(arquivo, id_trabalho, extensao)
    cv.adicionar(id_trabalho, entrada, nome_sem_extensao(arquivo.filename), modo, tamanho_mb, qualidade, resolucao)
    return jsonify({"id": id_trabalho, "status": "Na fila..."}), 202
