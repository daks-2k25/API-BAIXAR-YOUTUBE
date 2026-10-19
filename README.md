# Baixar YouTube

Aplicação em Python para baixar vídeos do YouTube em **MP4** ou extrair o áudio em **MP3**, além de converter fotos **HEIC** (iPhone) para **JPG**. Tem um **painel web** que abre sozinho no navegador e uma **API REST** por trás, feita com Flask e [yt-dlp](https://github.com/yt-dlp/yt-dlp).

## Início rápido (Windows)

1. Instale o que o projeto precisa (só na primeira vez):

   ```powershell
   winget install Python.Python.3.13
   winget install ffmpeg
   winget install DenoLand.Deno
   ```

   O **Deno** é opcional, mas recomendado: o yt-dlp usa ele para ler o YouTube, e sem ele alguns vídeos podem falhar.

2. Clone o repositório:

   ```bash
   git clone https://github.com/daks-2k25/API-BAIXAR-YOUTUBE.git
   cd API-BAIXAR-YOUTUBE
   ```

3. Dê dois cliques em **`iniciar.bat`**. Na primeira vez ele instala as dependências do Python. Depois disso, o painel abre sozinho no navegador em `http://localhost:5000`.

## Funcionalidades

- **Painel web** em HTML, CSS e JavaScript puros, servido pela própria aplicação
- Download de vídeo em **MP4** com **escolha de resolução** (360p, 480p, 720p ou 1080p), em H.264 para abrir em qualquer player
- Extração de áudio em **MP3** (192 kbps)
- **Até 3 downloads ao mesmo tempo**, com acompanhamento de progresso
- **Nova tentativa automática** quando o YouTube falha momentaneamente
- Links com playlist (`&list=...`) baixam só o vídeo, e não a playlist inteira
- Arquivos salvos com o **título do vídeo** no nome
- **Conversão de HEIC para JPG**
- **Limpeza automática**: o arquivo é apagado depois de baixado, ou após 30 minutos se ninguém baixar
- **Executável para Windows**, que não precisa de Python instalado

## Usando o painel

- **YouTube:** cole o link, escolha MP4 ou MP3 e a resolução, e clique em **Baixar agora**. Quando a barra completar, clique em **Salvar arquivo**.
- **HEIC → JPG:** arraste a foto ou clique para escolher. O JPG é baixado sozinho.
- **Para fechar:** use o botão **Encerrar programa** no fim do painel. Se o painel ficar fechado por 3 minutos e não houver downloads em andamento, o programa fecha sozinho.

O programa roda sem janela preta. Se clicar de novo com ele já aberto, só o navegador abre. As mensagens do programa ficam no arquivo `BaixarYouTube.log`, ao lado do programa, útil se algo der errado.

## Estrutura do projeto

```
API-BAIXAR-YOUTUBE/
├── iniciar.bat          # Dois cliques: abre o painel no navegador
├── app.py               # API (Flask) + inicialização
├── painel/              # Painel web (index.html, style.css, script.js)
│                        # + logo.svg, favicon.svg e icone.ico
├── servicos/
│   ├── caminhos.py      # Pastas do projeto (funciona também dentro do .exe)
│   ├── downloader.py    # Fila de downloads (yt-dlp)
│   ├── conversor.py     # Conversão de HEIC para JPG (FFmpeg)
│   └── limpeza.py       # Apaga arquivos esquecidos após 30 minutos
├── ferramentas/
│   └── gerar_exe.bat    # Gera o executável (PyInstaller)
├── requirements.txt
└── README.md
```

Ao rodar, a aplicação cria a pasta `downloads/` (arquivos temporários) e o `BaixarYouTube.log`. O `gerar_exe.bat` cria a pasta `BaixarYouTube/` e o atalho `Baixar YouTube.lnk`. Nada disso vai para o Git.

## Gerar o executável (Windows)

1. Dê dois cliques em `ferramentas\gerar_exe.bat`. Ele instala o PyInstaller, gera o programa na pasta `BaixarYouTube\` e cria o atalho **Baixar YouTube** na pasta principal.
2. Dê dois cliques no atalho **Baixar YouTube**.

O programa é gerado como pasta, e não como um `.exe` único, porque assim abre bem mais rápido. Para levar para outro PC, copie a pasta `BaixarYouTube\` inteira. Sempre que alterar o código, gere o executável de novo.

O FFmpeg não vai dentro do executável: ele precisa estar instalado no PC, ou o `ffmpeg.exe` precisa ficar dentro da pasta `BaixarYouTube\`.

## Rodando em outros sistemas (Linux/macOS)

Instale o Python 3 e o FFmpeg (`sudo apt install ffmpeg` ou `brew install ffmpeg`), depois:

```bash
pip install -r requirements.txt
python app.py
```

## API

A aplicação roda em `http://localhost:5000`.

### `POST /api/download`

Coloca um vídeo na fila de download.

| Campo       | Tipo   | Obrigatório | Descrição |
|-------------|--------|-------------|-----------|
| `url`       | string | Sim         | URL do vídeo |
| `formato`   | string | Não         | `mp4` (padrão) ou `mp3` |
| `qualidade` | string | Não         | Resolução máxima do MP4: `360p`, `480p`, `720p` (padrão) ou `1080p`. Ignorado no MP3 |
| `id`        | string | Não         | ID próprio do download: letras, números, `-` e `_`, até 64 caracteres. Se omitido, gera um UUID |

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

**Resposta `400 Bad Request`** quando falta a URL ou quando `formato`, `qualidade` ou `id` são inválidos:

```json
{ "erro": "Qualidade inválida. Opções: 360p, 480p, 720p, 1080p." }
```

Se o vídeo não tiver a resolução pedida, a API baixa a maior disponível abaixo dela.

### `GET /api/qualidades`

Lista as resoluções aceitas.

```json
{ "qualidades": ["360p", "480p", "720p", "1080p"], "padrao": "720p" }
```

### `GET /api/progresso/<id>`

Retorna o status do download. O `titulo` aparece quando o download fica pronto.

```json
{ "id": "3f2b8c1e-....", "status": "45.3%", "titulo": null }
```

| Status                   | Significado |
|--------------------------|-------------|
| `Na fila...`             | Aguardando a vez na fila |
| `Baixando...`            | Download iniciado |
| `xx.x%`                  | Progresso do download |
| `Processando arquivo...` | Download concluído, convertendo/juntando vídeo e áudio |
| `Pronto`                 | Arquivo disponível para baixar |
| `Erro`                   | Falha no download (depois de 2 tentativas) |
| `Desconhecido`           | ID não encontrado, arquivo já baixado ou expirado (30 min) |

### `GET /api/arquivo/<id>`

Baixa o arquivo final (`.mp4` ou `.mp3`), com o título do vídeo no nome. Depois do envio, o arquivo é apagado e o ID deixa de existir.

```bash
curl -OJ http://localhost:5000/api/arquivo/3f2b8c1e-....
```

Responde `404` se o arquivo ainda não estiver pronto ou já tiver sido baixado.

### `POST /api/converter/heic`

Converte uma imagem HEIC para JPG. Envie o arquivo como `multipart/form-data` no campo `arquivo`; a resposta é o JPG.

```bash
curl -X POST http://localhost:5000/api/converter/heic \
  -F "arquivo=@foto.heic" -OJ
```

| Código | Quando |
|--------|--------|
| `400`  | Nenhum arquivo enviado no campo `arquivo` |
| `500`  | Falha na conversão (o arquivo não é um HEIC válido) |

### `POST /api/ping` e `POST /api/encerrar`

Usadas pelo painel: o `ping` avisa a cada 30 segundos que o painel continua aberto, e o `encerrar` fecha o programa.

## Observações

- O status dos downloads fica em memória: ao fechar o programa, a fila e os status são perdidos.
- O servidor embutido do Flask é para uso local. Para hospedar em um servidor, use um servidor WSGI (ex.: Gunicorn ou Waitress) com **um único processo**, porque a fila fica em memória.
- Respeite os termos de uso das plataformas e os direitos autorais do conteúdo baixado.

## Licença

Este projeto está sob a licença MIT. Sinta-se à vontade para usar e modificar.
