# Baixar YouTube

Aplicação em Python para baixar vídeos do YouTube em **MP4** ou extrair o áudio em **MP3**, além de converter fotos **HEIC** (iPhone) para **JPG**. Abre numa **janela própria**, com uma **API REST** por trás, feita com Flask e [yt-dlp](https://github.com/yt-dlp/yt-dlp).

## Início rápido (Windows)

1. Baixe o projeto: **Code → Download ZIP** no GitHub (e descompacte) ou `git clone https://github.com/daks-2k25/API-BAIXAR-YOUTUBE.git`.
2. Dê dois cliques em **`iniciar.bat`**.

Pronto. **Na primeira vez**, ele instala sozinho o que estiver faltando no PC:

- **uv**: cuida do Python e das bibliotecas. Usa o Python que já estiver no PC ou baixa um, sem instalar nada no Windows
- **FFmpeg**: junta vídeo e áudio, gera MP3 e converte HEIC
- **Deno**: o yt-dlp usa para ler o YouTube

O uv, o FFmpeg e o Deno vêm pelo winget, que já vem no Windows 10 e 11. Isso leva alguns minutos e mostra o andamento numa janela. **Nas próximas vezes**, ele vê que está tudo pronto e abre o programa em cerca de 2 segundos.

No primeiro clique ele também cria o atalho **Baixar YouTube**, com a logo, na **Área de Trabalho**. Depois é só usar o atalho. Se você apagar o atalho, ele não é criado de novo; se mover a pasta do projeto, o atalho é corrigido no próximo uso do `iniciar.bat`. O yt-dlp é atualizado automaticamente uma vez por dia, porque o YouTube muda com frequência.

> Se o Windows mostrar "O Windows protegeu o computador" ao abrir o `iniciar.bat` baixado da internet, clique em **Mais informações → Executar assim mesmo**.

## Funcionalidades

- **Janela própria** (não precisa do navegador): fechar a janela fecha o programa
- **Atualização pelo próprio programa**: quando sai uma versão nova, aparece um aviso com as novidades e o botão **Atualizar agora**
- **Notificações**: sino 🔔 com bolinha quando há versão nova, notificação no canto da janela e verificação automática a cada 30 minutos com o programa aberto
- **Prévia do vídeo** ao colar o link: miniatura, título, canal e duração, com opção de assistir ali mesmo para conferir antes de baixar
- Download de vídeo em **MP4** com **escolha de resolução** (360p, 480p, 720p ou 1080p), em H.264 para abrir em qualquer player
- Extração de áudio em **MP3** (192 kbps)
- **Até 3 downloads ao mesmo tempo**, com acompanhamento de progresso
- **Nova tentativa automática** quando o YouTube falha momentaneamente
- **Playlists bloqueadas**: o painel avisa quando o link é de uma playlist e não deixa baixar. Se for um vídeo aberto dentro de uma playlist, oferece o botão **Usar só este vídeo**
- **Salva direto na pasta Downloads**, com o **título do vídeo** no nome (sem sobrescrever arquivos que já existem)
- **Cortar um trecho**: baixa só o pedaço escolhido (ex.: de 1:20 a 2:05), cortado no segundo exato
- **Cancelar** downloads na fila ou em andamento
- **Conversão de HEIC para JPG**, salvo direto em Downloads
- **Executável para Windows**, que não precisa de Python instalado e mantém o yt-dlp atualizado sozinho

## Usando o programa

- **YouTube:** cole o link e confira a prévia do vídeo (clique na miniatura para assistir ali mesmo). Escolha MP4 ou MP3 e a resolução, e clique em **Baixar agora**. O arquivo é salvo na sua pasta **Downloads**; o botão **Mostrar na pasta** abre o Explorador com ele selecionado.
- **Cortar trecho:** clique em **✂ Cortar trecho** e preencha o início e o fim (ex.: `1:20` e `2:05`). Deixe o fim vazio para ir até o final do vídeo.
- **Cancelar:** cada download tem um botão **✕ Cancelar** enquanto está na fila ou baixando.
- **HEIC → JPG:** arraste a foto ou clique para escolher. O JPG é salvo na pasta Downloads.
- **Atualizar:** quando sair uma versão nova, aparece uma notificação no canto da janela, um aviso no topo e uma bolinha no sino 🔔. Clique em **Atualizar agora**: o programa baixa a versão nova, reinicia sozinho e continua com seus arquivos e configurações. Com o programa aberto, ele confere se saiu versão nova a cada 30 minutos. A versão instalada aparece no rodapé.
- **Depois:** se preferir atualizar mais tarde, clique em **Depois**. A notificação não volta para essa versão (o sino continua com a bolinha, e a atualização fica disponível nele). Se sair uma versão ainda mais nova, o programa avisa de novo.
- **Sino 🔔:** mostra a atualização disponível ou confirma que você está na versão mais recente, com o botão **Verificar agora**.
- **Para fechar:** feche a janela. Se ainda houver download em andamento, o programa pergunta antes.

Se clicar no atalho com o programa já aberto, a janela só vem para a frente. As mensagens do programa ficam no arquivo `BaixarYouTube.log`, útil se algo der errado. Se a janela própria não puder ser criada no PC (ex.: sem o componente WebView2 do Windows), o painel abre no navegador, como alternativa.

### Como a atualização funciona

- **Projeto baixado como ZIP:** o programa baixa o ZIP novo do GitHub e substitui os arquivos do projeto. A pasta `downloads`, o ambiente do Python (`.ambiente`), os logs e o atalho não são tocados. Arquivos que saíram do projeto na versão nova são apagados.
- **Projeto clonado com git:** o programa roda `git pull`, mas só se a pasta estiver na branch `main` e sem alterações locais no código. Assim, quem está desenvolvendo não tem o trabalho sobrescrito.
- **Programa gerado (`BaixarYouTube.exe`):** o aviso aparece, mas para atualizar é preciso gerar o programa de novo.

## Publicando uma versão nova

1. Faça as mudanças e aumente o número em **`versao.json`** (ex.: de `2.0.0` para `2.1.0`), escrevendo as novidades na lista `novidades`. É esse texto que aparece no aviso para os usuários.
2. Suba para a branch `main` do GitHub.

Na próxima vez que alguém abrir o programa, o aviso de atualização aparece.

## Estrutura do projeto

```
API-BAIXAR-YOUTUBE/
├── iniciar.bat          # Dois cliques: prepara tudo e abre o programa
├── app.py               # API (Flask + Waitress), janela própria e inicialização
├── versao.json          # Versão do programa e novidades (usado na atualização)
├── pyproject.toml       # Bibliotecas do Python (usado pelo uv)
├── painel/              # Painel (index.html, style.css, script.js)
│                        # + logo.webp, favicon.svg e icone.ico (ícone do programa)
├── servicos/
│   ├── caminhos.py      # Pastas do projeto e pasta Downloads do usuário
│   ├── autoatualizacao.py # Botão "Atualizar agora": baixa e instala a versão nova
│   ├── atualizador.py   # Mantém o yt-dlp atualizado dentro do executável
│   ├── downloader.py    # Fila de downloads, corte de trecho e cancelamento (yt-dlp)
│   ├── informacoes.py   # Prévia do vídeo (título, canal, duração, miniatura)
│   └── conversor.py     # Conversão de HEIC para JPG (FFmpeg)
├── logos/               # Identidade visual: logo e ícones em SVG, PNG e WebP
├── ferramentas/
│   ├── iniciar.ps1      # Usado pelo iniciar.bat: instala o que faltar, cria o atalho e abre o programa
│   └── gerar_exe.bat    # Gera o executável (PyInstaller)
└── README.md
```

Ao rodar, a aplicação cria a pasta `.ambiente/` (Python e bibliotecas, preparada pelo uv), a pasta `downloads/` (arquivos temporários enquanto baixa; os prontos vão para a pasta Downloads do Windows) e o `BaixarYouTube.log`. O `gerar_exe.bat` cria a pasta `BaixarYouTube/` e o atalho `Baixar YouTube.lnk`. Nada disso vai para o Git.

## Gerar o executável (Windows)

1. Rode o `iniciar.bat` pelo menos uma vez (ele instala o uv).
2. Dê dois cliques em `ferramentas\gerar_exe.bat`. Ele gera o programa na pasta `BaixarYouTube\` e cria o atalho **Baixar YouTube** na pasta principal.
3. Dê dois cliques no atalho **Baixar YouTube** da pasta principal.

O programa é gerado como pasta, e não como um `.exe` único, porque assim abre bem mais rápido. Para levar para outro PC, copie a pasta `BaixarYouTube\` inteira. Sempre que alterar o código, gere o executável de novo.

O yt-dlp vai empacotado no programa, mas **se atualiza sozinho**: uma vez por dia o programa procura uma versão nova no PyPI, baixa (conferindo o SHA-256) e passa a usá-la na próxima abertura. As versões baixadas ficam em `BaixarYouTube\atualizacoes\`.

O FFmpeg não vai dentro do executável: ele precisa estar instalado no PC, ou o `ffmpeg.exe` precisa ficar dentro da pasta `BaixarYouTube\`.

## Rodando em outros sistemas (Linux/macOS)

Instale o [uv](https://docs.astral.sh/uv/) e o FFmpeg (`sudo apt install ffmpeg` ou `brew install ffmpeg`), depois:

```bash
uv run app.py
```

## API

A aplicação roda em `http://127.0.0.1:5000`.

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
curl -X POST http://127.0.0.1:5000/api/download \
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
curl -OJ http://127.0.0.1:5000/api/arquivo/3f2b8c1e-....
```

Responde `404` se o arquivo ainda não estiver pronto ou não for encontrado.

### `POST /api/converter/heic`

Converte uma imagem HEIC para JPG. Envie o arquivo como `multipart/form-data` no campo `arquivo`; a resposta é o JPG.

```bash
curl -X POST http://127.0.0.1:5000/api/converter/heic \
  -F "arquivo=@foto.heic" -OJ
```

| Código | Quando |
|--------|--------|
| `400`  | Nenhum arquivo enviado no campo `arquivo` |
| `500`  | Falha na conversão (o arquivo não é um HEIC válido) |

### `POST /api/ping` e `POST /api/encerrar`

Usadas pelo painel: o `ping` avisa a cada 30 segundos que o painel continua aberto, e o `encerrar` fecha o programa.

### `GET /api/versao`

Versão instalada e, se houver, a versão nova no GitHub. Adicione `?forcar=1` para não usar a consulta guardada (o resultado fica guardado por 10 minutos).

```json
{ "atual": "2.0.0", "nova": "2.1.0", "novidades": ["..."], "disponivel": true, "pode_atualizar": true, "motivo": null }
```

`pode_atualizar` é `false` no programa gerado (`.exe`) e em pastas git fora da `main` ou com alterações locais; `motivo` explica o porquê.

### `POST /api/versao/adiar`

Corpo: `{"versao": "2.1.0"}`. Usado pelo botão **Depois**: o painel não mostra de novo a notificação dessa versão (o `GET /api/versao` passa a responder `"adiada": true`). Fica guardado em `.preferencias.json`.

### `POST /api/atualizar`

Baixa e instala a versão nova e reinicia o programa. Responde `409` se houver downloads em andamento.

### `GET /api/modo` e `POST /api/focar`

Usadas pela janela do programa: `modo` diz se o painel está na janela própria (`{"janela": true}`) ou no navegador, e `focar` traz a janela para a frente (é o que acontece ao clicar no atalho com o programa já aberto).

## Observações

- O status dos downloads fica em memória: ao fechar o programa, a fila e os status são perdidos.
- O servidor (Waitress) atende só o próprio PC (`127.0.0.1`). Para hospedar num servidor de verdade, use **um único processo**, porque a fila de downloads fica em memória.
- Respeite os termos de uso das plataformas e os direitos autorais do conteúdo baixado.

## Licença

Este projeto está sob a licença MIT. Sinta-se à vontade para usar e modificar.
