# API de Download de Vídeos (Flask + yt-dlp)

API REST em Python para baixar vídeos (MP4) ou extrair o áudio (MP3) a partir de uma URL, usando o [yt-dlp](https://github.com/yt-dlp/yt-dlp). Os downloads entram numa fila e são processados um de cada vez em segundo plano; o cliente acompanha o progresso e baixa o arquivo quando ele estiver pronto.

## Funcionalidades

- Download de vídeo em **MP4** (melhor qualidade de vídeo + áudio disponível)
- Extração de áudio em **MP3** (192 kbps)
- **Fila de processamento** em background (um download por vez, sem travar a API)
- **Acompanhamento de progresso** em porcentagem
- **Limpeza automática**: o arquivo é apagado do servidor depois de ser baixado
- **CORS** habilitado, pronto para ser consumido por um frontend

## Tecnologias

- [Python 3](https://www.python.org/)
- [Flask](https://flask.palletsprojects.com/)
- [Flask-CORS](https://flask-cors.readthedocs.io/)
- [yt-dlp](https://github.com/yt-dlp/yt-dlp)
- [FFmpeg](https://ffmpeg.org/) (necessário para juntar vídeo/áudio e converter para MP3)

## Estrutura do projeto

```
API-BAIXAR-YOUTUBE/
├── app.py          # Rotas da API (Flask)
├── downloader.py   # Fila e worker de download (yt-dlp)
├── requirements.txt
└── downloads/      # Pasta temporária dos arquivos gerados
```

## Instalação

1. Clone o repositório:

   ```bash
   git clone https://github.com/daks-2k25/API-BAIXAR-YOUTUBE.git
   cd API-BAIXAR-YOUTUBE
   ```

2. (Opcional) Crie e ative um ambiente virtual:

   ```bash
   python -m venv venv
   # Windows
   venv\Scripts\activate
   # Linux/macOS
   source venv/bin/activate
   ```

3. Instale as dependências:

   ```bash
   pip install -r requirements.txt
   ```

4. Instale o **FFmpeg** e garanta que ele esteja no `PATH`:
   - Windows: `winget install ffmpeg` (ou baixe em [ffmpeg.org](https://ffmpeg.org/download.html))
   - Linux: `sudo apt install ffmpeg`
   - macOS: `brew install ffmpeg`

## Como executar

```bash
python app.py
```

A API sobe em `http://localhost:5000`.

## Endpoints

### `POST /api/download`

Coloca um vídeo na fila de download.

**Body (JSON):**

| Campo     | Tipo   | Obrigatório | Descrição                                          |
|-----------|--------|-------------|----------------------------------------------------|
| `url`     | string | Sim         | URL do vídeo                                       |
| `formato` | string | Não         | `mp4` (padrão) ou `mp3`                            |
| `id`      | string | Não         | ID próprio do download (se omitido, gera um UUID)  |

**Exemplo:**

```bash
curl -X POST http://localhost:5000/api/download \
  -H "Content-Type: application/json" \
  -d '{"url": "https://www.youtube.com/watch?v=XXXXXXXXXXX", "formato": "mp3"}'
```

**Resposta `202 Accepted`:**

```json
{
  "mensagem": "Vídeo enfileirado com sucesso!",
  "id": "3f2b8c1e-....",
  "status": "Na fila..."
}
```

**Resposta `400 Bad Request`** (sem URL):

```json
{ "erro": "A URL do video e obrigatoria." }
```

---

### `GET /api/progresso/<id>`

Retorna o status atual do download.

```bash
curl http://localhost:5000/api/progresso/3f2b8c1e-....
```

```json
{ "id": "3f2b8c1e-....", "status": "45.3%" }
```

Valores possíveis de `status`:

| Status                   | Significado                                   |
|--------------------------|-----------------------------------------------|
| `Na fila...`             | Aguardando a vez na fila                      |
| `Baixando...`            | Download iniciado                             |
| `xx.x%`                  | Progresso do download                         |
| `Processando arquivo...` | Download concluído, convertendo/mesclando     |
| `Pronto`                 | Arquivo disponível para baixar                |
| `Erro`                   | Falha no download                             |
| `Desconhecido`           | ID não encontrado (ou arquivo já foi baixado) |

---

### `GET /api/arquivo/<id>`

Baixa o arquivo final (`.mp4` ou `.mp3`). Depois do envio, o arquivo é **removido do servidor** e o ID deixa de existir.

```bash
curl -OJ http://localhost:5000/api/arquivo/3f2b8c1e-....
```

**Resposta `404 Not Found`** se o arquivo ainda não estiver pronto ou já tiver sido baixado:

```json
{ "erro": "Arquivo ainda não está pronto ou já foi baixado." }
```

## Fluxo de uso

1. Envie a URL com `POST /api/download` e guarde o `id` retornado.
2. Consulte `GET /api/progresso/<id>` periodicamente até o status ser `Pronto`.
3. Baixe o arquivo com `GET /api/arquivo/<id>`.

## Observações

- O status dos downloads fica em memória: ao reiniciar a API, a fila e os status são perdidos.
- A API roda em modo `debug` por padrão; para produção, use um servidor WSGI (ex.: Gunicorn ou Waitress) e desative o debug.
- Respeite os termos de uso das plataformas e os direitos autorais do conteúdo baixado.

## Licença

Este projeto está sob a licença MIT. Sinta-se à vontade para usar e modificar.
