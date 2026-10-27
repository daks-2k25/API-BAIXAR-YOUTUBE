"""Endereços da API (/api/...) usados pelo painel, um arquivo por área:

- videos.py       baixar vídeos e músicas (YouTube, TikTok, Instagram)
- fotos.py        converter e comprimir fotos
- arquivos.py     mostrar na pasta, abrir e "Meus downloads"
- programa.py     janela ou navegador, preferências, encerrar
- atualizacao.py  versão nova e botão "Atualizar agora"
"""
from flask import Flask, send_from_directory
from flask_cors import CORS

from servicos.caminhos import PASTA_PAINEL
from rotas import arquivos, atualizacao, fotos, programa, videos


def criar_app():
    # O painel web (pasta painel/) é servido pela própria API em http://localhost:5000
    app = Flask(__name__, static_folder=PASTA_PAINEL, static_url_path="")
    CORS(app)

    @app.route('/')
    def painel():
        return send_from_directory(PASTA_PAINEL, "index.html")

    for modulo in (videos, fotos, arquivos, programa, atualizacao):
        app.register_blueprint(modulo.rotas)
    return app
