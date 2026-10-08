import os
import threading
import time

# Arquivos prontos que ninguém baixou são apagados depois desse tempo
TEMPO_MAXIMO_SEGUNDOS = 30 * 60
INTERVALO_VERIFICACAO = 60

# caminho do arquivo -> (momento em que ficou pronto, função chamada ao apagar)
arquivos_temporarios = {}
trava = threading.Lock()


def registrar_arquivo(caminho, ao_apagar=None):
    """Marca um arquivo gerado pela API para ser apagado se ficar esquecido."""
    with trava:
        arquivos_temporarios[caminho] = (time.time(), ao_apagar)


def limpar_arquivos_antigos():
    """Fica rodando em segundo plano apagando arquivos expirados."""
    while True:
        time.sleep(INTERVALO_VERIFICACAO)
        agora = time.time()

        with trava:
            expirados = [
                (caminho, ao_apagar)
                for caminho, (momento, ao_apagar) in arquivos_temporarios.items()
                if agora - momento > TEMPO_MAXIMO_SEGUNDOS
            ]
            for caminho, _ in expirados:
                del arquivos_temporarios[caminho]

        for caminho, ao_apagar in expirados:
            try:
                # Se o usuário já baixou, o arquivo não existe mais
                if os.path.exists(caminho):
                    os.remove(caminho)
                    print(f"[LIMPEZA] Arquivo expirado removido: {caminho}")
                if ao_apagar:
                    ao_apagar()
            except Exception as e:
                print(f"[LIMPEZA] Erro ao remover {caminho}: {e}")


# Inicializa a Thread de limpeza em background assim que o módulo é importado
t = threading.Thread(target=limpar_arquivos_antigos, daemon=True)
t.start()
