"""O programa em si: janela ou navegador, preferências e encerrar."""
import threading
import webbrowser

from flask import Blueprint, jsonify, request

from servicos import preferencias, programa
from servicos.janela import trazer_para_frente

rotas = Blueprint("programa", __name__)


@rotas.route('/api/modo', methods=['GET'])
def modo_api():
    # O painel esconde o botão "Encerrar" quando está na janela própria
    return jsonify({
        "janela": programa.na_janela(),
        "preferencia": preferencias.modo_de_abertura(),
    })


@rotas.route('/api/ping', methods=['POST'])
def ping_api():
    # No modo navegador, o painel avisa a cada 30 segundos que continua aberto
    programa.painel_deu_sinal()
    return jsonify({"ok": True})


@rotas.route('/api/encerrar', methods=['POST'])
def encerrar_api():
    # Responde primeiro e fecha logo depois, para o painel receber a resposta
    programa.encerrar_em_instantes()
    return jsonify({"mensagem": "Programa encerrado."})


@rotas.route('/api/focar', methods=['POST'])
def focar_api():
    # Clicou no atalho com o programa já aberto: traz a janela para a frente
    if programa.janela is not None:
        trazer_para_frente()
    else:
        webbrowser.open(programa.ENDERECO_PAINEL)
    return jsonify({"ok": True})


@rotas.route('/api/preferencias', methods=['GET'])
def preferencias_api():
    return jsonify({"modo_abertura": preferencias.modo_de_abertura()})


@rotas.route('/api/preferencias', methods=['POST'])
def salvar_preferencias_api():
    # Configurações do painel: abrir sempre na janela do aplicativo ou no navegador
    modo = (request.get_json(silent=True) or {}).get("modo_abertura")
    if modo not in preferencias.MODOS_DE_ABERTURA:
        return jsonify({"erro": "Use 'janela' ou 'navegador'."}), 400
    preferencias.salvar("modo_abertura", modo)
    return jsonify({"modo_abertura": modo})


@rotas.route('/api/abrir-no-navegador', methods=['POST'])
def abrir_no_navegador_api():
    # Abre o painel no navegador agora e fecha a janela; o programa continua rodando
    if programa.janela is not None:
        programa.trocando_para_navegador = True
        threading.Timer(0.3, programa.janela.destroy).start()
    webbrowser.open(programa.ENDERECO_PAINEL)
    return jsonify({"ok": True})


@rotas.route('/api/reabrir-como-aplicativo', methods=['POST'])
def reabrir_como_aplicativo_api():
    # No navegador: reinicia o programa já na janela do aplicativo
    if programa.na_janela():
        return jsonify({"erro": "O programa já está aberto como aplicativo."}), 409
    programa.reiniciar("janela")
    programa.encerrar_em_instantes()
    return jsonify({"ok": True})
