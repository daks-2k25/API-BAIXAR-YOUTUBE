# API de Download de Vídeos (Flask + yt-dlp)

API REST em Python para baixar vídeos (MP4) ou extrair o áudio (MP3) a partir de uma URL, usando o [yt-dlp](https://github.com/yt-dlp/yt-dlp). Os downloads entram numa fila e são processados um de cada vez em segundo plano; o cliente acompanha o progresso e baixa o arquivo quando ele estiver pronto.

## Funcionalidades

- Download de vídeo em **MP4** com **escolha de resolução** (360p, 480p, 720p ou 1080p)
- Extração de áudio em **MP3** (192 kbps)
- **Fila de processamento** em background (um download por vez, sem travar a API)
- **Acompanhamento de progresso** em porcentagem
- **Conversão de imagens HEIC** (fotos do iPhone) para **JPG**
- **Limpeza automática**: o arquivo é apagado do servidor depois de ser baixado, ou após 30 minutos se ninguém baixar
- **CORS** habilitado, pronto para ser consumido por um frontend

## Tecnologias

- [Python 3](https://www.python.org/)
- [Flask](https://flask.palletsprojects.com/)
- [Flask-CORS](https://flask-cors.readthedocs.io/)
- [yt-dlp](https://github.com/yt-dlp/yt-dlp)
- [FFmpeg](https://ffmpeg.org/) (necessário para juntar vídeo/áudio, converter para MP3 e converter HEIC para JPG)

## Estrutura do projeto

```
API-BAIXAR-YOUTUBE/
├── app.py               # Rotas da API (Flask)
├── servicos/
│   ├── downloader.py    # Fila e worker de download (yt-dlp)
│   ├── conversor.py     # Conversão de HEIC para JPG (FFmpeg)
│   └── limpeza.py       # Apaga arquivos esquecidos após 30 minutos
├── downloads/           # Pasta temporária dos arquivos gerados
├── requirements.txt
└── README.md
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
| `qualidade` | string | Não       | Resolução máxima do MP4: `360p`, `480p`, `720p` (padrão) ou `1080p`. Ignorado no MP3 |
| `id`      | string | Não         | ID próprio do download: letras, números, `-` e `_`, até 64 caracteres (se omitido, gera um UUID) |

**Exemplo:**

```bash
curl -X POST http://localhost:5000/api/download \
  -H "Content-Type: application/json" \
  -d '{"url": "https://www.youtube.com/watch?v=XXXXXXXXXXX", "formato": "mp4", "qualidade": "1080p"}'
```

**Resposta `202 Accepted`:**

```json
{
  "mensagem": "Vídeo enfileirado com sucesso!",
  "id": "3f2b8c1e-....",
  "formato": "mp4",
  "qualidade": "1080p",
  "status": "Na fila..."
}
```

**Resposta `400 Bad Request`**: quando falta a URL ou quando `formato`, `qualidade` ou `id` são inválidos.

```json
{ "erro": "Qualidade inválida. Opções: 360p, 480p, 720p, 1080p." }
```

Se o vídeo não tiver a resolução pedida, a API baixa a maior disponível abaixo dela.

---

### `GET /api/qualidades`

Lista as resoluções aceitas, útil para montar o seletor no frontend.

```json
{ "qualidades": ["360p", "480p", "720p", "1080p"], "padrao": "720p" }
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
| `Desconhecido`           | ID não encontrado, arquivo já baixado ou expirado (30 min) |

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

---

### `POST /api/converter/heic`

Converte uma imagem HEIC para JPG e devolve o JPG para download. Envie o arquivo como `multipart/form-data` no campo `arquivo`.

```bash
curl -X POST http://localhost:5000/api/converter/heic   -F "arquivo=@foto.heic" -OJ
```

A resposta `200` é o arquivo `foto.jpg`. Os arquivos temporários são apagados do servidor logo após o envio.

**Erros:**

| Código | Quando                                                 |
|--------|--------------------------------------------------------|
| `400`  | Nenhum arquivo enviado no campo `arquivo`              |
| `500`  | Falha na conversão (o arquivo não é um HEIC válido)    |

## Fluxo de uso (download de vídeo)

1. Envie a URL com `POST /api/download` e guarde o `id` retornado.
2. Consulte `GET /api/progresso/<id>` periodicamente até o status ser `Pronto`.
3. Baixe o arquivo com `GET /api/arquivo/<id>`.

## Observações

- O status dos downloads fica em memória: ao reiniciar a API, a fila e os status são perdidos.
- Arquivos prontos que não forem baixados em 30 minutos são apagados automaticamente.
- A API roda em modo `debug` por padrão; para produção, use um servidor WSGI (ex.: Gunicorn ou Waitress) e desative o debug.
- Respeite os termos de uso das plataformas e os direitos autorais do conteúdo baixado.

## Licença

Este projeto está sob a licença MIT. Sinta-se à vontade para usar e modificar.
