"""Ícone do Puxaí na bandeja do Windows (perto do relógio).

- Clique: abre o Puxaí (traz a janela para a frente ou abre o painel no navegador)
- Botão direito: menu com Abrir, Abrir no navegador, Abrir a pasta dos
  arquivos e Encerrar (que pergunta antes se ainda há algo em andamento)
- Ao parar o mouse: "Puxaí", ou "Puxaí · 3 em andamento"

Feito direto com as funções do Windows (ctypes), sem biblioteca a mais: a
mais usada para isso (pystray) depende do Pillow, e o Controle Inteligente de
Aplicativos do Windows já bloqueou uma DLL parecida (a do pillow-heif).

Roda numa thread própria, com o próprio "laço de mensagens" do Windows. Fechar
a janela do aplicativo continua encerrando o programa; o ícone sai junto.
"""
import ctypes
import os
import sys
import threading
import webbrowser
from ctypes import wintypes

from servicos import destinos, programa
from servicos.caminhos import PASTA_PAINEL
from servicos.downloader import quantos_em_andamento

if sys.platform == "win32":
    user32 = ctypes.windll.user32
    shell32 = ctypes.windll.shell32
    kernel32 = ctypes.windll.kernel32

CLASSE_JANELA = "PuxaiBandeja"
ID_ICONE = 1

WM_APP_BANDEJA = 0x8000 + 1  # WM_APP + 1: a mensagem que o ícone manda para a janela
WM_COMMAND, WM_TIMER, WM_DESTROY, WM_NULL = 0x0111, 0x0113, 0x0002, 0x0000
WM_LBUTTONUP, WM_RBUTTONUP, WM_CONTEXTMENU = 0x0202, 0x0205, 0x007B
NIM_ADD, NIM_MODIFY, NIM_DELETE = 0, 1, 2
NIF_MESSAGE, NIF_ICON, NIF_TIP = 0x1, 0x2, 0x4
MF_STRING, MF_SEPARATOR = 0x0, 0x800
TPM_RIGHTBUTTON, TPM_RETURNCMD, TPM_NONOTIFY = 0x2, 0x100, 0x80
IMAGE_ICON, LR_LOADFROMFILE = 1, 0x10
MB_YESNO, MB_ICONQUESTION, MB_TOPMOST, MB_SETFOREGROUND, IDYES = 0x4, 0x20, 0x40000, 0x10000, 6

# Itens do menu (também chegam como WM_COMMAND, o que facilita testar)
ABRIR, NAVEGADOR, PASTA, ENCERRAR = 1, 2, 3, 4
ITENS_DO_MENU = [
    (ABRIR, "Abrir o Puxaí"),
    (NAVEGADOR, "Abrir no navegador"),
    (PASTA, "Abrir a pasta dos arquivos"),
    (None, None),  # separador
    (ENCERRAR, "Encerrar o Puxaí"),
]

LRESULT = ctypes.c_ssize_t
WNDPROC = ctypes.WINFUNCTYPE(LRESULT, wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM)


class WNDCLASSEXW(ctypes.Structure):
    _fields_ = [
        ("cbSize", wintypes.UINT), ("style", wintypes.UINT), ("lpfnWndProc", WNDPROC),
        ("cbClsExtra", ctypes.c_int), ("cbWndExtra", ctypes.c_int), ("hInstance", wintypes.HINSTANCE),
        ("hIcon", wintypes.HICON), ("hCursor", wintypes.HANDLE), ("hbrBackground", wintypes.HBRUSH),
        ("lpszMenuName", wintypes.LPCWSTR), ("lpszClassName", wintypes.LPCWSTR), ("hIconSm", wintypes.HICON),
    ]


class GUID(ctypes.Structure):
    _fields_ = [("Data1", wintypes.DWORD), ("Data2", wintypes.WORD), ("Data3", wintypes.WORD),
                ("Data4", ctypes.c_ubyte * 8)]


class NOTIFYICONDATAW(ctypes.Structure):
    _fields_ = [
        ("cbSize", wintypes.DWORD), ("hWnd", wintypes.HWND), ("uID", wintypes.UINT), ("uFlags", wintypes.UINT),
        ("uCallbackMessage", wintypes.UINT), ("hIcon", wintypes.HICON), ("szTip", wintypes.WCHAR * 128),
        ("dwState", wintypes.DWORD), ("dwStateMask", wintypes.DWORD), ("szInfo", wintypes.WCHAR * 256),
        ("uVersion", wintypes.UINT), ("szInfoTitle", wintypes.WCHAR * 64), ("dwInfoFlags", wintypes.DWORD),
        ("guidItem", GUID), ("hBalloonIcon", wintypes.HICON),
    ]


class _Bandeja:
    def __init__(self):
        self.janela = None
        self.dados = None
        self.dica = None
        self._procedimento = WNDPROC(self._mensagem)  # guardado: o Windows chama esta função depois
        self._taskbar_criada = None

    # ---------- ícone ----------

    def _mostrar(self, operacao=NIM_ADD):
        return bool(shell32.Shell_NotifyIconW(operacao, ctypes.byref(self.dados)))

    def _atualizar_dica(self):
        quantos = quantos_em_andamento()
        dica = "Puxaí" if not quantos else f"Puxaí · {quantos} em andamento"
        if dica != self.dica:
            self.dica = dica
            self.dados.szTip = dica
            self._mostrar(NIM_MODIFY)

    def remover(self):
        if self.dados is not None:
            shell32.Shell_NotifyIconW(NIM_DELETE, ctypes.byref(self.dados))

    # ---------- ações (numa thread à parte: não travam o ícone) ----------

    def _executar(self, comando):
        threading.Thread(target=self._acao, args=(comando,), daemon=True).start()

    def _acao(self, comando):
        try:
            if comando == ABRIR:
                if programa.na_janela():
                    from servicos.janela import trazer_para_frente
                    trazer_para_frente()
                else:
                    webbrowser.open(programa.ENDERECO_PAINEL)
            elif comando == NAVEGADOR:
                webbrowser.open(programa.ENDERECO_PAINEL)
            elif comando == PASTA:
                pastas = destinos.configuracao()
                os.startfile(destinos.pasta_para("video") if pastas["modo"] == "separadas" else pastas["tudo"])
            elif comando == ENCERRAR:
                quantos = quantos_em_andamento()
                if quantos and user32.MessageBoxW(
                    None,
                    f"Ainda há {quantos} {'item' if quantos == 1 else 'itens'} em andamento "
                    "(downloads ou compressões). Se encerrar agora, eles serão interrompidos.\n\nEncerrar mesmo assim?",
                    "Encerrar o Puxaí?", MB_YESNO | MB_ICONQUESTION | MB_TOPMOST | MB_SETFOREGROUND,
                ) != IDYES:
                    return
                programa.encerrar()
        except Exception as e:
            print(f"[BANDEJA] Não foi possível executar a ação {comando}: {e}")

    def _menu(self):
        menu = user32.CreatePopupMenu()
        for comando, texto in ITENS_DO_MENU:
            if comando is None:
                user32.AppendMenuW(menu, MF_SEPARATOR, 0, None)
            else:
                user32.AppendMenuW(menu, MF_STRING, comando, texto)
        user32.SetMenuDefaultItem(menu, ABRIR, False)  # "Abrir" em negrito (é o do clique)
        ponto = wintypes.POINT()
        user32.GetCursorPos(ctypes.byref(ponto))
        # Sem isto o menu não fecha ao clicar fora (comportamento conhecido do Windows)
        user32.SetForegroundWindow(self.janela)
        comando = user32.TrackPopupMenu(menu, TPM_RIGHTBUTTON | TPM_RETURNCMD | TPM_NONOTIFY,
                                        ponto.x, ponto.y, 0, self.janela, None)
        user32.PostMessageW(self.janela, WM_NULL, 0, 0)
        user32.DestroyMenu(menu)
        if comando:
            self._executar(comando)

    # ---------- mensagens do Windows ----------

    def _mensagem(self, janela, mensagem, wparam, lparam):
        if mensagem == WM_APP_BANDEJA:
            if lparam == WM_LBUTTONUP:
                self._executar(ABRIR)
            elif lparam in (WM_RBUTTONUP, WM_CONTEXTMENU):
                self._menu()
            return 0
        if mensagem == WM_COMMAND:
            self._executar(wparam & 0xFFFF)
            return 0
        if mensagem == WM_TIMER:
            self._atualizar_dica()
            return 0
        if mensagem == self._taskbar_criada:
            # O Explorador do Windows reiniciou e apagou os ícones: põe o nosso de novo
            self._mostrar(NIM_ADD)
            return 0
        if mensagem == WM_DESTROY:
            self.remover()
            user32.PostQuitMessage(0)
            return 0
        return user32.DefWindowProcW(janela, mensagem, wparam, lparam)

    def rodar(self):
        modulo = kernel32.GetModuleHandleW(None)
        classe = WNDCLASSEXW(cbSize=ctypes.sizeof(WNDCLASSEXW), lpfnWndProc=self._procedimento,
                             hInstance=modulo, lpszClassName=CLASSE_JANELA)
        user32.RegisterClassExW(ctypes.byref(classe))
        # Janela invisível que só recebe as mensagens do ícone
        self.janela = user32.CreateWindowExW(0, CLASSE_JANELA, "Puxaí (bandeja)", 0, 0, 0, 0, 0,
                                             None, None, modulo, None)
        if not self.janela:
            raise OSError("não foi possível criar a janela da bandeja")
        self._taskbar_criada = user32.RegisterWindowMessageW("TaskbarCreated")

        tamanho = user32.GetSystemMetrics(49)  # SM_CXSMICON: tamanho do ícone pequeno
        icone = user32.LoadImageW(None, os.path.join(PASTA_PAINEL, "icone.ico"), IMAGE_ICON,
                                  tamanho, tamanho, LR_LOADFROMFILE)
        self.dados = NOTIFYICONDATAW(cbSize=ctypes.sizeof(NOTIFYICONDATAW), hWnd=self.janela, uID=ID_ICONE,
                                     uFlags=NIF_MESSAGE | NIF_ICON | NIF_TIP,
                                     uCallbackMessage=WM_APP_BANDEJA, hIcon=icone, szTip="Puxaí")
        self.dica = "Puxaí"
        if not self._mostrar(NIM_ADD):
            raise OSError("o Windows não aceitou o ícone na bandeja")
        programa.ao_encerrar.append(self.remover)
        user32.SetTimer(self.janela, 1, 2000, None)  # atualiza a dica ("3 em andamento") a cada 2 s

        mensagem = wintypes.MSG()
        while user32.GetMessageW(ctypes.byref(mensagem), None, 0, 0) > 0:
            user32.TranslateMessage(ctypes.byref(mensagem))
            user32.DispatchMessageW(ctypes.byref(mensagem))


def _declarar_tipos():
    """No Windows 64 bits, os identificadores não cabem num int comum: declara os tipos."""
    user32.DefWindowProcW.restype = LRESULT
    user32.DefWindowProcW.argtypes = [wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]
    user32.CreateWindowExW.restype = wintypes.HWND
    user32.CreateWindowExW.argtypes = [wintypes.DWORD, wintypes.LPCWSTR, wintypes.LPCWSTR, wintypes.DWORD,
                                       ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int, wintypes.HWND,
                                       wintypes.HMENU, wintypes.HINSTANCE, wintypes.LPVOID]
    user32.LoadImageW.restype = wintypes.HANDLE
    user32.LoadImageW.argtypes = [wintypes.HINSTANCE, wintypes.LPCWSTR, wintypes.UINT, ctypes.c_int,
                                  ctypes.c_int, wintypes.UINT]
    user32.CreatePopupMenu.restype = wintypes.HMENU
    user32.AppendMenuW.argtypes = [wintypes.HMENU, wintypes.UINT, ctypes.c_size_t, wintypes.LPCWSTR]
    user32.SetMenuDefaultItem.argtypes = [wintypes.HMENU, wintypes.UINT, wintypes.UINT]
    user32.TrackPopupMenu.argtypes = [wintypes.HMENU, wintypes.UINT, ctypes.c_int, ctypes.c_int, ctypes.c_int,
                                      wintypes.HWND, wintypes.LPVOID]
    user32.DestroyMenu.argtypes = [wintypes.HMENU]
    user32.PostMessageW.argtypes = [wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]
    user32.SetForegroundWindow.argtypes = [wintypes.HWND]
    user32.SetTimer.argtypes = [wintypes.HWND, ctypes.c_size_t, wintypes.UINT, wintypes.LPVOID]
    user32.MessageBoxW.argtypes = [wintypes.HWND, wintypes.LPCWSTR, wintypes.LPCWSTR, wintypes.UINT]
    kernel32.GetModuleHandleW.restype = wintypes.HMODULE
    shell32.Shell_NotifyIconW.argtypes = [wintypes.DWORD, ctypes.POINTER(NOTIFYICONDATAW)]


def iniciar():
    """Põe o ícone na bandeja (numa thread própria). Se não der, o programa segue sem ele."""
    if sys.platform != "win32":
        return

    def rodar():
        try:
            _declarar_tipos()
            _Bandeja().rodar()
        except Exception as e:
            print(f"[BANDEJA] Ícone da bandeja indisponível: {e}")

    threading.Thread(target=rodar, daemon=True, name="bandeja").start()
