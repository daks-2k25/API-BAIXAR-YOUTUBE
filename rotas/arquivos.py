"""Arquivos já salvos: mostrar na pasta, abrir e a lista de "Meus downloads"."""
import os

from flask import Blueprint, jsonify

from rotas.utilidades import caminho_do_arquivo
from servicos import historico, sistema

rotas = Blueprint("arquivos", __name__)

NAO_ENCONTRADO = {"erro": "Arquivo não encontrado (foi movido ou apagado?)."}


@rotas.route('/api/mostrar/<id_arquivo>', methods=['POST'])
def mostrar_na_pasta_api(id_arquivo):
    # Abre a pasta (Explorador de Arquivos, no Windows) com o arquivo baixado selecionado
    caminho = caminho_do_arquivo(id_arquivo)
    if not caminho or not os.path.exists(caminho):
        return jsonify(NAO_ENCONTRADO), 404
    sistema.mostrar_na_pasta(caminho)
    return jsonify({"mensagem": "Pasta aberta."})


@rotas.route('/api/abrir/<id_arquivo>', methods=['POST'])
def abrir_arquivo_api(id_arquivo):
    # Abre o arquivo no programa padrão do sistema (player de vídeo, música, fotos)
    caminho = caminho_do_arquivo(id_arquivo)
    if not caminho or not os.path.exists(caminho):
        return jsonify(NAO_ENCONTRADO), 404
    sistema.abrir(caminho)
    return jsonify({"mensagem": "Arquivo aberto."})


@rotas.route('/api/historico', methods=['GET'])
def historico_api():
    return jsonify(historico.listar())


@rotas.route('/api/historico/<id_arquivo>', methods=['DELETE'])
def remover_do_historico_api(id_arquivo):
    # Só tira da lista: o arquivo continua na pasta Downloads
    if not historico.remover(id_arquivo):
        return jsonify({"erro": "Esse item não está no histórico."}), 404
    return jsonify({"mensagem": "Removido da lista."})


@rotas.route('/api/historico', methods=['DELETE'])
def limpar_historico_api():
    historico.limpar()
    return jsonify({"mensagem": "Histórico limpo."})
