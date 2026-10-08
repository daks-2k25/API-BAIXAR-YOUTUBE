from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
from werkzeug.wsgi import ClosingIterator
import os
import re
import uuid

# Importando as ferramentas da pasta servicos/
from servicos.downloader import adicionar_fila, status_download
from servicos.conversor import converter_heic_para_jpg
import servicos.limpeza  # Inicia a limpeza automática de arquivos esquecidos

app = Flask(__name__)
CORS(app)

PASTA_DOWNLOADS = "downloads"
if not os.path.exists(PASTA_DOWNLOADS):
    os.makedirs(PASTA_DOWNLOADS)


# Resoluções permitidas para MP4 (máximo 1080p para não pesar no servidor)
QUALIDADES_PERMITIDAS = [360, 480, 720, 1080]
QUALIDADE_PADRAO = 720

# O ID vira nome de arquivo: só letras, números, "-" e "_" (evita acessar outras pastas)
PADRAO_ID = re.compile(r'^[A-Za-z0-9_-]{1,64}$')


def ao_terminar_envio(resposta, funcao):
    """Executa a função só depois que o arquivo foi enviado e fechado.
    (No Windows não dá para apagar um arquivo que ainda está aberto.)"""
    resposta.response = ClosingIterator(resposta.response, funcao)
    return resposta

# ==========================================
# FERRAMENTA 1: YOUTUBE DOWNLOADER
# ==========================================

@app.route('/api/download', methods=['POST'])
def download_api():
    dados = request.get_json()

    if not dados or 'url' not in dados:
        return jsonify({"erro": "A URL do video e obrigatoria."}), 400

    url = dados['url']
    formato = dados.get('formato', 'mp4')
    id_download = str(dados.get('id', uuid.uuid4()))

    if formato not in ('mp4', 'mp3'):
        return jsonify({"erro": "Formato inválido. Use 'mp4' ou 'mp3'."}), 400

    if not PADRAO_ID.match(id_download):
        return jsonify({"erro": "ID inválido. Use só letras, números, '-' e '_' (até 64 caracteres)."}), 400

    try:
        qualidade = int(str(dados.get('qualidade', QUALIDADE_PADRAO)).lower().rstrip('p'))
    except ValueError:
        qualidade = None

    if qualidade not in QUALIDADES_PERMITIDAS:
        return jsonify({
            "erro": f"Qualidade inválida. Opções: {', '.join(f'{q}p' for q in QUALIDADES_PERMITIDAS)}."
        }), 400

    extensao = "mp3" if formato == "mp3" else "mp4"
    caminho_final = os.path.join(PASTA_DOWNLOADS, f"{id_download}.{extensao}")

    adicionar_fila(url, formato, qualidade, id_download, caminho_final)

    return jsonify({
        "mensagem": "Vídeo enfileirado com sucesso!",
        "id": id_download,
        "formato": formato,
        "qualidade": f"{qualidade}p" if formato == "mp4" else None,
        "status": "Na fila..."
    }), 202


@app.route('/api/qualidades', methods=['GET'])
def qualidades_api():
    # Para o frontend montar a lista de opções
    return jsonify({
        "qualidades": [f"{q}p" for q in QUALIDADES_PERMITIDAS],
        "padrao": f"{QUALIDADE_PADRAO}p"
    })

@app.route('/api/progresso/<id_download>', methods=['GET'])
def progresso_api(id_download):
    status = status_download.get(id_download, "Desconhecido")
    return jsonify({"id": id_download, "status": status})

@app.route('/api/arquivo/<id_download>', methods=['GET'])
def baixar_arquivo_api(id_download):
    if not PADRAO_ID.match(id_download):
        return jsonify({"erro": "ID inválido."}), 400

    caminho_mp4 = os.path.join(PASTA_DOWNLOADS, f"{id_download}.mp4")
    caminho_mp3 = os.path.join(PASTA_DOWNLOADS, f"{id_download}.mp3")
    
    caminho_arquivo = None
    if os.path.exists(caminho_mp4):
        caminho_arquivo = caminho_mp4
    elif os.path.exists(caminho_mp3):
        caminho_arquivo = caminho_mp3

    if caminho_arquivo and os.path.exists(caminho_arquivo):
        resposta = send_file(caminho_arquivo, as_attachment=True)

        def remover_arquivo():
            try:
                os.remove(caminho_arquivo)
                if id_download in status_download:
                    del status_download[id_download]
            except Exception as e:
                print(f"Erro ao limpar arquivo: {e}")

        return ao_terminar_envio(resposta, remover_arquivo)
    
    return jsonify({"erro": "Arquivo ainda não está pronto ou já foi baixado."}), 404


# ==========================================
# FERRAMENTA 2: CONVERSOR DE HEIC PARA JPG
# ==========================================

@app.route('/api/converter/heic', methods=['POST'])
def converter_heic_api():
    if 'arquivo' not in request.files:
        return jsonify({"erro": "Nenhum arquivo enviado. Use o campo 'arquivo' no form-data."}), 400

    arquivo = request.files['arquivo']
    
    if arquivo.filename == '':
        return jsonify({"erro": "Nenhum arquivo selecionado."}), 400

    # Gera um ID para a imagem e salva temporariamente
    id_conversao = str(uuid.uuid4())
    caminho_heic = os.path.join(PASTA_DOWNLOADS, f"{id_conversao}.heic")
    arquivo.save(caminho_heic)

    # Aciona o seu conversor.py
    caminho_jpg = converter_heic_para_jpg(caminho_heic)

    if caminho_jpg and os.path.exists(caminho_jpg):
        nome_download = arquivo.filename.rsplit('.', 1)[0] + ".jpg"
        resposta = send_file(caminho_jpg, as_attachment=True, download_name=nome_download)

        def limpar_arquivos():
            try:
                if os.path.exists(caminho_heic):
                    os.remove(caminho_heic)
                if os.path.exists(caminho_jpg):
                    os.remove(caminho_jpg)
                print(f"Limpeza: Arquivos {id_conversao} removidos com sucesso.")
            except Exception as e:
                print(f"Erro ao limpar arquivos: {e}")

        return ao_terminar_envio(resposta, limpar_arquivos)
        
    else:
        if os.path.exists(caminho_heic):
            os.remove(caminho_heic)
        return jsonify({"erro": "Falha na conversão. Verifique se o arquivo é um HEIC válido."}), 500


if __name__ == "__main__":
    app.run(debug=True, port=5000)