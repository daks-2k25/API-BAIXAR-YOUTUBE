from flask import Flask, request, jsonify, send_file, after_this_request
from flask_cors import CORS
from downloader import adicionar_fila, status_download
import os
import uuid

app = Flask(__name__)
CORS(app)

PASTA_DOWNLOADS = "downloads"
if not os.path.exists(PASTA_DOWNLOADS):
    os.makedirs(PASTA_DOWNLOADS)

@app.route('/api/download', methods=['POST'])
def download_api():
    dados = request.get_json()

    if not dados or 'url' not in dados:
        return jsonify({"erro": "A URL do video e obrigatoria."}), 400

    url = dados['url']
    formato = dados.get('formato', 'mp4')
    id_download = dados.get('id', str(uuid.uuid4()))

    # Define o caminho fixo onde o worker vai salvar o arquivo final deste ID
    # Usamos o ID no nome para evitar conflitos de arquivos com nomes iguais
    extensao = "mp3" if formato == "mp3" else "mp4"
    caminho_final = os.path.join(PASTA_DOWNLOADS, f"{id_download}.{extensao}")

    # Envia para a fila (retorna na hora para o frontend)
    adicionar_fila(url, formato, id_download, caminho_final)

    return jsonify({
        "mensagem": "Vídeo enfileirado com sucesso!",
        "id": id_download,
        "status": "Na fila..."
    }), 202


@app.route('/api/progresso/<id_download>', methods=['GET'])
def progresso_api(id_download):
    status = status_download.get(id_download, "Desconhecido")
    return jsonify({"id": id_download, "status": status})


@app.route('/api/arquivo/<id_download>', methods=['GET'])
def baixar_arquivo_api(id_download):
    # Procura se existe o arquivo gerado para esse ID (mp4 ou mp3)
    caminho_mp4 = os.path.join(PASTA_DOWNLOADS, f"{id_download}.mp4")
    caminho_mp3 = os.path.join(PASTA_DOWNLOADS, f"{id_download}.mp3")
    
    caminho_arquivo = None
    if os.path.exists(caminho_mp4):
        caminho_arquivo = caminho_mp4
    elif os.path.exists(caminho_mp3):
        caminho_arquivo = caminho_mp3

    if caminho_arquivo and os.path.exists(caminho_arquivo):
        @after_this_request
        def remover_arquivo(response):
            try:
                os.remove(caminho_arquivo)
                if id_download in status_download:
                    del status_download[id_download]
                print(f"Limpeza: Arquivo {caminho_arquivo} removido após o download.")
            except Exception as e:
                print(f"Erro ao limpar arquivo: {e}")
            return response

        return send_file(caminho_arquivo, as_attachment=True)
    
    return jsonify({"erro": "Arquivo ainda não está pronto ou já foi baixado."}), 404


if __name__ == "__main__":
    app.run(debug=True, port=5000)