# Baixar YouTube

Aplicação em Python para baixar vídeos do YouTube em **MP4** ou extrair o áudio em **MP3**, além de converter fotos **HEIC** (iPhone) para **JPG**. Tem um **painel web** que abre sozinho no navegador e uma **API REST** por trás, feita com Flask e [yt-dlp](https://github.com/yt-dlp/yt-dlp).

## Início rápido (Windows)

1. Baixe o projeto: **Code → Download ZIP** no GitHub (e descompacte) ou `git clone https://github.com/daks-2k25/API-BAIXAR-YOUTUBE.git`.
2. Dê dois cliques em **`iniciar.bat`**.

Pronto. **Na primeira vez**, ele instala sozinho o que estiver faltando no PC, usando o winget (que já vem no Windows 10 e 11):

- **Python**
- **FFmpeg**: junta vídeo e áudio, gera MP3 e converte HEIC
- **Deno**: o yt-dlp usa para ler o YouTube
- as **bibliotecas do Python** (Flask, yt-dlp...)

Isso leva alguns minutos e mostra o andamento numa janela. **Nas próximas vezes**, ele vê que está tudo pronto e abre o painel no navegador em cerca de 2 segundos. O yt-dlp é atualizado automaticamente uma vez por dia, porque o YouTube muda com frequência.

> Se o Windows mostrar "O Windows protegeu o computador" ao abrir o `iniciar.bat` baixado da internet, clique em **Mais informações → Executar assim mesmo**.

## Funcionalidades

- **Painel web** em HTML, CSS e JavaScript puros, servido pela própria aplicação
- **Prévia do vídeo** ao colar o link: miniatura, título, canal e duração, com opção de assistir ali mesmo para conferir antes de baixar
- Download de vídeo em **MP4** com **escolha de resolução** (360p, 480p, 720p ou 1080p), em H.264 para abrir em qualquer player
- Extração de áudio em **MP3** (192 kbps)
- **Até 3 downloads ao mesmo tempo**, com acompanhamento de progresso
- **Nova tentativa automática** quando o YouTube falha momentaneamente
- **Playlists bloqueadas**: o painel avisa quando o link é de uma playlist e não deixa baixar. Se for um vídeo aberto dentro de uma playlist, oferece o botão **Usar só este vídeo**
- **Salva direto na pasta Downloads**, com o **título do vídeo** no nome (sem sobrescrever arquivos que já existem)
- **Cortar um trecho**: baixa só o pedaço escolhido (ex.: de 1:20 a 2:05), cortado no segundo exato
- **Cancelar** downloads na fila ou em andamento
- **Conversão de HEIC para JPG**
- **Executável para Windows**, que não precisa de Python instalado e mantém o yt-dlp atualizado sozinho

## Usando o painel

- **YouTube:** cole o link e confira a prévia do vídeo (clique na miniatura para assistir ali mesmo). Escolha MP4 ou MP3 e a resolução, e clique em **Baixar agora**. O arquivo é salvo na sua pasta **Downloads**; o botão **Mostrar na pasta** abre o Explorador com ele selecionado.
- **Cortar trecho:** clique em **✂ Cortar trecho** e preencha o início e o fim (ex.: `1:20` e `2:05`). Deixe o fim vazio para ir até o final do vídeo.
- **Cancelar:** cada download tem um botão **✕ Cancelar** enquanto está na fila ou baixando.
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
│   ├── caminhos.py      # Pastas do projeto e pasta Downloads do usuário
│   ├── atualizador.py   # Mantém o yt-dlp atualizado dentro do executável
│   ├── downloader.py    # Fila de downloads, corte de trecho e cancelamento (yt-dlp)
│   ├── informacoes.py   # Prévia do vídeo (título, canal, duração, miniatura)
│   └── conversor.py     # Conversão de HEIC para JPG (FFmpeg)
├── ferramentas/
│   ├── iniciar.ps1      # Usado pelo iniciar.bat: instala o que faltar e abre o programa
│   └── gerar_exe.bat    # Gera o executável (PyInstaller)
├── requirements.txt
└── README.md
```

Ao rodar, a aplicação cria a pasta `downloads/` (arquivos temporários enquanto baixa; os prontos vão para a pasta Downloads do Windows) e o `BaixarYouTube.log`. O `gerar_exe.bat` cria a pasta `BaixarYouTube/` e o atalho `Baixar YouTube.lnk`. Nada disso vai para o Git.

## Gerar o executável (Windows)

1. Dê dois cliques em `ferramentas\gerar_exe.bat`. Ele instala o PyInstaller, gera o programa na pasta `BaixarYouTube\` e cria o atalho **Baixar YouTube** na pasta principal.
2. Dê dois cliques no atalho **Baixar YouTube**.

O programa é gerado como pasta, e não como um `.exe` único, porque assim abre bem mais rápido. Para levar para outro PC, copie a pasta `BaixarYouTube\` inteira. Sempre que alterar o código, gere o executável de novo.

O yt-dlp vai empacotado no programa, mas **se atualiza sozinho**: uma vez por dia o programa procura uma versão nova no PyPI, baixa (conferindo o SHA-256) e passa a usá-la na próxima abertura. As versões baixadas ficam em `BaixarYouTube\atualizacoes\`.

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
| `inicio`    | string | Não         | Início do trecho a baixar: `1:20`, `1:02:05` ou segundos |
| `fim`       | string | Não         | Fim do trecho. Sem `fim`, vai até o final do vídeo |

O arquivo pronto é salvo na pasta **Downloads** do usuário, com o título do vídeo no nome (e o trecho, se houver).

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
  "trecho": null,
  "status": "Na fila..."
}
```

**Resposta `400 Bad Request`** quando falta a URL, quando `formato`, `qualidade`, `id` ou o trecho são inválidos, ou quando o link é de uma playlist inteira (`youtube.com/playlist?list=...`). Um vídeo dentro de uma playlist (`watch?v=...&list=...`) é aceito, e só o vídeo é baixado:

```json
{ "erro": "Qualidade inválida. Opções: 360p, 480p, 720p, 1080p." }
```

Se o vídeo não tiver a resolução pedida, a API baixa a maior disponível abaixo dela.

### `GET /api/info?url=<link>`

Prévia do vídeo, sem baixar nada. Usada pelo painel ao colar um link.

```json
{
  "id": "TO-_3tck2tg",
  "titulo": "Imagine Dragons - Bones (Official Music Video)",
  "canal": "ImagineDragons",
  "duracao": "2:45",
  "miniatura": "https://i.ytimg.com/vi/TO-_3tck2tg/maxresdefault.jpg",
  "youtube": true
}
```

Responde `400` para links de playlist e `404` quando o vídeo não é encontrado.

### `GET /api/qualidades`

Lista as resoluções aceitas.

```json
{ "qualidades": ["360p", "480p", "720p", "1080p"], "padrao": "720p" }
```

### `GET /api/progresso/<id>`

Retorna o status do download. Quando fica pronto, `titulo` e `arquivo` (nome do arquivo na pasta Downloads) são preenchidos.

```json
{ "id": "3f2b8c1e-....", "status": "Pronto", "titulo": "Me at the zoo", "arquivo": "Me at the zoo.mp4" }
```

| Status                   | Significado |
|--------------------------|-------------|
| `Na fila...`             | Aguardando a vez na fila |
| `Baixando...`            | Download iniciado |
| `xx.x%`                  | Progresso do download |
| `Processando arquivo...` | Download concluído, convertendo/juntando vídeo e áudio |
| `Pronto`                 | Arquivo salvo na pasta Downloads |
| `Erro`                   | Falha no download (depois de 2 tentativas) |
| `Cancelado`              | Cancelado pelo usuário |
| `Desconhecido`           | ID não encontrado |

### `POST /api/cancelar/<id>`

Cancela um download na fila ou em andamento; os arquivos parciais são apagados. Responde `404` se o download não existe ou já terminou.

### `POST /api/mostrar/<id>`

Abre o Explorador de Arquivos com o arquivo pronto selecionado (usado pelo botão **Mostrar na pasta**).

### `GET /api/arquivo/<id>`

Envia o arquivo pronto pela resposta HTTP, para quem usa a API a partir de outro programa. O arquivo continua na pasta Downloads.

```bash
curl -OJ http://localhost:5000/api/arquivo/3f2b8c1e-....
```

Responde `404` se o arquivo ainda não estiver pronto ou não for encontrado.

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
