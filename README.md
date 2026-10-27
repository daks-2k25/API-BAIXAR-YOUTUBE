# Puxaí

Aplicação em Python para baixar vídeos do **YouTube**, **TikTok** e **Instagram** em **MP4** ou extrair o áudio em **MP3**, além de converter e comprimir fotos (**HEIC**, **JPG**, **PNG** e **WebP**). Abre numa **janela própria**, com uma **API REST** por trás, feita com Flask e [yt-dlp](https://github.com/yt-dlp/yt-dlp).

## Início rápido (Windows)

1. Baixe o projeto: **Code → Download ZIP** no GitHub (e descompacte) ou `git clone https://github.com/daks-2k25/API-BAIXAR-YOUTUBE.git`.
2. Dê dois cliques em **`iniciar.bat`**.

Pronto. **Na primeira vez**, ele instala sozinho o que estiver faltando no PC:

- **uv**: cuida do Python e das bibliotecas. Usa o Python que já estiver no PC ou baixa um, sem instalar nada no Windows
- **FFmpeg**: junta vídeo e áudio, gera MP3 e converte as fotos
- **Deno**: o yt-dlp usa para ler o YouTube

O uv, o FFmpeg e o Deno vêm pelo winget, que já vem no Windows 10 e 11. Isso leva alguns minutos e mostra o andamento numa janela. **Nas próximas vezes**, ele vê que está tudo pronto e abre o programa em cerca de 2 segundos.

No primeiro clique ele também cria o atalho **Puxaí**, com a logo, na **Área de Trabalho** (quem já tinha o atalho antigo, **Baixar YouTube**, tem ele renomeado sozinho). Depois é só usar o atalho. Se você apagar o atalho, ele não é criado de novo; se mover a pasta do projeto, o atalho é corrigido no próximo uso do `iniciar.bat`. O yt-dlp é atualizado automaticamente uma vez por dia, porque o YouTube muda com frequência.

> Se o Windows mostrar "O Windows protegeu o computador" ao abrir o `iniciar.bat` baixado da internet, clique em **Mais informações → Executar assim mesmo**.

## Funcionalidades

- **Janela própria ou navegador**: abre como aplicativo (fechar a janela fecha o programa) ou, se preferir, no navegador. Dá para escolher em **⚙ Configurações**
- **Atualização pelo próprio programa**: quando sai uma versão nova, aparece um aviso com as novidades e o botão **Atualizar agora**
- **Notificações**: sino 🔔 com bolinha quando há versão nova, notificação no canto da janela e verificação automática a cada 30 minutos com o programa aberto
- **Prévia do vídeo** ao colar o link: miniatura, título, canal e duração, com opção de assistir ali mesmo para conferir antes de baixar
- **YouTube, TikTok e Instagram** (vídeos e reels): é só colar o link
- Download de vídeo em **MP4** com **escolha de resolução** (360p, 480p, 720p ou 1080p), inclusive em vídeos verticais (TikTok, Reels, Shorts). No TikTok, sempre a versão **sem marca d'água**
- Extração de áudio em **MP3** (192 kbps) com **capa e informações**: a miniatura do vídeo vira a capa (quadrada, como a de um álbum), e o MP3 leva título, artista, álbum (quando o YouTube informa) e ano, para aparecer certinho no player e no celular. O título sai sem o artista na frente e sem "(Official Video)", "[Lyrics]" e parecidos; no comentário vai o link do vídeo
- **Até 3 downloads ao mesmo tempo**, com acompanhamento de progresso
- **Nova tentativa automática** quando o YouTube falha momentaneamente
- **Playlists e canais**: cole o link e aparece a lista de vídeos (até 200) com caixinhas para marcar quais baixar. Os arquivos podem ir para uma pasta com o nome da playlist, numerados na ordem (`01 - Título`), bom para álbuns. Se o link for de um vídeo aberto dentro de uma playlist, o painel pergunta: **Usar só este vídeo** ou **Baixar a playlist**
- **Vários links de uma vez**: cole uma lista de links (até 200) e todos entram na fila, na ordem
- **Cancelar todos**: com 2 ou mais downloads em andamento, um botão cancela todos de uma vez
- **Salva direto na pasta Downloads**, com o **título do vídeo** no nome (sem sobrescrever arquivos que já existem)
- **Cortar um trecho**: baixa só o pedaço escolhido (ex.: de 1:20 a 2:05), cortado no segundo exato
- **Cancelar** downloads na fila ou em andamento
- **Conversão de fotos**: HEIC para JPG, e HEIC, JPG ou PNG para WebP (bem menor, mantém a transparência do PNG), salvo direto em Downloads
- **Compressor de fotos**: JPG, PNG, WebP e HEIC, uma ou várias de uma vez. Testa algumas qualidades em cada foto e fica com o menor arquivo que continua visualmente igual (medido pelo SSIM), em três níveis. Nunca deixa o arquivo maior, corrige a orientação das fotos de celular, remove a localização (GPS) e pode reduzir o tamanho (2560, 1920 ou 1280 px)
- **Meus downloads**: lista do que o programa já salvou (vídeos, músicas e fotos), com filtros, **Abrir** e **Mostrar na pasta**, mesmo depois de fechar e abrir o programa
- **Executável para Windows**, que não precisa de Python instalado e mantém o yt-dlp atualizado sozinho

## Usando o programa

- **Baixar:** cole o link do YouTube, TikTok ou Instagram e confira a prévia do vídeo (no YouTube, clique na miniatura para assistir ali mesmo). Escolha MP4 ou MP3 e a resolução, e clique em **Baixar agora**. O arquivo é salvo na sua pasta **Downloads**; o botão **Mostrar na pasta** abre o Explorador com ele selecionado.
- **Vários links:** cole vários links de uma vez no campo (o painel percebe e abre uma caixa com um link por linha) ou clique em **+ Colar vários links de uma vez**. Os links podem estar um por linha, separados por espaço ou no meio de outro texto; repetidos contam uma vez só (inclusive o mesmo vídeo do YouTube escrito de jeitos diferentes). O formato e a qualidade escolhidos valem para todos. Vídeo aberto dentro de uma playlist baixa só o vídeo; o link de uma playlist inteira precisa ser colado sozinho, para escolher os vídeos.
- **Cortar trecho:** clique em **✂ Cortar trecho** e preencha o início e o fim (ex.: `1:20` e `2:05`). Deixe o fim vazio para ir até o final do vídeo.
- **Cancelar:** cada download tem um botão **✕ Cancelar** enquanto está na fila ou baixando.
- **Converter foto:** escolha **JPG** (a partir de HEIC) ou **WebP** (a partir de HEIC, JPG ou PNG), depois arraste uma ou várias fotos (ou clique para escolher). Elas são convertidas uma de cada vez, cada uma aparece na lista com o resultado, e as convertidas vão para a pasta Downloads. Se uma foto não for aceita (ex.: PNG para JPG), só ela mostra o erro e as outras continuam.
- **Comprimir foto:** escolha o nível (**Alta qualidade**, **Equilibrado** ou **Máxima compressão**) e, se quiser, um tamanho máximo, e arraste uma ou várias fotos. Cada foto aparece com o tamanho antes e depois, e a versão comprimida vai para Downloads com "(comprimida)" no nome. JPG, PNG e WebP continuam no mesmo formato; HEIC vira JPG. Se a foto já estiver bem comprimida, nada é salvo.
- **Meus downloads:** mostra tudo o que o programa salvou, do mais novo para o mais antigo, com data e tamanho. Filtre por **Vídeos**, **Músicas** ou **Fotos**, e use **Abrir** (abre no player ou visualizador do Windows) ou **Mostrar na pasta**. **Remover da lista** e **Limpar lista** só tiram da lista: os arquivos continuam na pasta Downloads. Se um arquivo foi apagado ou movido, ele aparece riscado.
- **Atualizar:** quando sair uma versão nova, aparece uma notificação no canto da janela, um aviso no topo e uma bolinha no sino 🔔. Clique em **Atualizar agora**: o programa baixa a versão nova, reinicia sozinho e continua com seus arquivos e configurações. Com o programa aberto, ele confere se saiu versão nova a cada 30 minutos. A versão instalada aparece no rodapé.
- **Depois:** se preferir atualizar mais tarde, clique em **Depois**. A notificação não volta para essa versão (o sino continua com a bolinha, e a atualização fica disponível nele). Se sair uma versão ainda mais nova, o programa avisa de novo.
- **Sino 🔔:** mostra a atualização disponível ou confirma que você está na versão mais recente, com o botão **Verificar agora**.
- **Para fechar:** feche a janela. Se ainda houver download em andamento, o programa pergunta antes.
- **Janela ou navegador:** em **⚙ Configurações** (ao lado do sino), escolha se o programa abre na **Janela do aplicativo** ou no **Navegador**. A escolha fica salva para as próximas vezes. Para trocar na hora:
  - Na janela, o botão **↗** (ou **Abrir no navegador agora**, nas Configurações) abre o painel no navegador e fecha a janela; o programa continua rodando.
  - No navegador, **Reabrir como aplicativo** (nas Configurações) reinicia o programa na janela.
  - No navegador, o programa fecha pelo botão **Encerrar programa** ou sozinho, 3 minutos depois de fechar todas as abas (se não houver downloads).

Se clicar no atalho com o programa já aberto, ele só traz a janela para a frente (ou abre o painel no navegador, se estiver nesse modo). As mensagens do programa ficam no arquivo `Puxai.log`, útil se algo der errado. Se a janela própria não puder ser criada no PC (ex.: sem o componente WebView2 do Windows), o painel abre no navegador, como alternativa.

### Instagram: posts que pedem login

Reels e vídeos **públicos** do Instagram baixam sem login. Se algum post só abrir com uma conta logada, o programa avisa. Nesse caso:

1. No Chrome, logado no Instagram, instale a extensão **Get cookies.txt LOCALLY**.
2. Abra o instagram.com, clique na extensão e exporte os cookies.
3. Salve o arquivo com o nome **`cookies.txt`** na pasta do programa (ao lado do `iniciar.bat`, ou dentro de `Puxai\` no programa gerado).

O programa passa a usar esse login automaticamente. O `cookies.txt` dá acesso à sua conta: não compartilhe esse arquivo. Ele não vai para o Git e o botão de atualizar não mexe nele.

> O yt-dlp não consegue ler os cookies do Chrome direto no Windows (o Chrome protege esses dados), por isso o caminho é exportar o arquivo. O Instagram baixa os vídeos; fotos de posts não são baixadas.

### Como a atualização funciona

- **Projeto baixado como ZIP:** o programa baixa o ZIP novo do GitHub e substitui os arquivos do projeto. A pasta `downloads`, o ambiente do Python (`.ambiente`), os logs e o atalho não são tocados. Arquivos que saíram do projeto na versão nova são apagados.
- **Projeto clonado com git:** o programa roda `git pull`, mas só se a pasta estiver na branch `main` e sem alterações locais no código. Assim, quem está desenvolvendo não tem o trabalho sobrescrito.
- **Programa gerado (`Puxai.exe`):** o aviso aparece, mas para atualizar é preciso gerar o programa de novo.

## Publicando uma versão nova

1. Faça as mudanças e aumente o número em **`versao.json`** (ex.: de `2.0.0` para `2.1.0`), escrevendo as novidades na lista `novidades`. É esse texto que aparece no aviso para os usuários.
2. Suba para a branch `main` do GitHub.

Na próxima vez que alguém abrir o programa, o aviso de atualização aparece.

## Estrutura do projeto

```
API-BAIXAR-YOUTUBE/
├── iniciar.bat          # Dois cliques: prepara tudo e abre o programa
├── app.py               # Início do programa: liga o servidor e abre a janela ou o navegador
├── versao.json          # Versão do programa e novidades (usado na atualização)
├── pyproject.toml       # Bibliotecas do Python (usado pelo uv)
├── painel/              # Painel (index.html, style.css, script.js)
│                        # + logo.webp, favicon.svg e icone.ico (ícone do programa)
├── rotas/               # Endereços da API (/api/...), um arquivo por área
│   ├── __init__.py      # Cria o app Flask e registra todas as rotas
│   ├── seguranca.py     # Só o painel pode usar a API (bloqueia pedidos de outros sites)
│   ├── videos.py        # Baixar, prévia, qualidades, progresso e cancelar
│   ├── fotos.py         # Converter e comprimir fotos
│   ├── arquivos.py      # Mostrar na pasta, abrir e "Meus downloads"
│   ├── programa.py      # Janela ou navegador, preferências, encerrar
│   ├── atualizacao.py   # Versão nova e "Atualizar agora"
│   └── utilidades.py    # O que as rotas compartilham (arquivos enviados, salvar em Downloads)
├── servicos/            # O que o programa faz (as rotas só chamam estes arquivos)
│   ├── programa.py      # Porta, uma instância só, reiniciar, encerrar e estado da janela
│   ├── janela.py        # Janela própria (pywebview) e ícone na barra de tarefas
│   ├── caminhos.py      # Pastas do projeto e pasta Downloads do usuário
│   ├── preferencias.py  # Preferências salvas (.preferencias.json): modo de abertura, atualização adiada
│   ├── historico.py     # Aba "Meus downloads": o que o programa salvou (.historico.json)
│   ├── compressor.py    # Aba "Comprimir foto": menor arquivo sem perda visível (FFmpeg + SSIM)
│   ├── autoatualizacao.py # Botão "Atualizar agora": baixa e instala a versão nova
│   ├── atualizador.py   # Mantém o yt-dlp atualizado dentro do executável
│   ├── downloader.py    # Fila de downloads, corte de trecho e cancelamento (yt-dlp)
│   ├── informacoes.py   # Prévia do vídeo (título, canal, duração, miniatura)
│   ├── sites.py         # O que é comum a YouTube, TikTok e Instagram (títulos, login, mensagens de erro)
│   └── conversor.py     # Conversão de fotos: HEIC -> JPG e HEIC/JPG/PNG -> WebP (FFmpeg)
├── logos/               # Identidade visual: logo e ícones em SVG, PNG e WebP
├── ferramentas/
│   ├── iniciar.ps1      # Usado pelo iniciar.bat: instala o que faltar, cria o atalho e abre o programa
│   └── gerar_exe.bat    # Gera o executável (PyInstaller)
└── README.md
```

Ao rodar, a aplicação cria a pasta `.ambiente/` (Python e bibliotecas, preparada pelo uv), a pasta `downloads/` (arquivos temporários enquanto baixa; os prontos vão para a pasta Downloads do Windows) e o `Puxai.log`. O `gerar_exe.bat` cria a pasta `Puxai/` e o atalho `Puxaí.lnk`. Nada disso vai para o Git.

## Gerar o executável (Windows)

1. Rode o `iniciar.bat` pelo menos uma vez (ele instala o uv).
2. Dê dois cliques em `ferramentas\gerar_exe.bat`. Ele gera o programa na pasta `Puxai\` e cria o atalho **Puxaí** na pasta principal.
3. Dê dois cliques no atalho **Puxaí** da pasta principal.

O programa é gerado como pasta, e não como um `.exe` único, porque assim abre bem mais rápido. Para levar para outro PC, copie a pasta `Puxai\` inteira. Sempre que alterar o código, gere o executável de novo.

O yt-dlp vai empacotado no programa, mas **se atualiza sozinho**: uma vez por dia o programa procura uma versão nova no PyPI, baixa (conferindo o SHA-256) e passa a usá-la na próxima abertura. As versões baixadas ficam em `Puxai\atualizacoes\`.

O FFmpeg não vai dentro do executável: ele precisa estar instalado no PC, ou o `ffmpeg.exe` precisa ficar dentro da pasta `Puxai\`.

## Rodando em outros sistemas (Linux/macOS)

Instale o [uv](https://docs.astral.sh/uv/) e o FFmpeg (`sudo apt install ffmpeg` ou `brew install ffmpeg`), depois:

```bash
uv run app.py
```

## API

A aplicação roda em `http://127.0.0.1:5000`.

**Segurança:** só o painel do programa pode usar a API pelo navegador. Pedidos vindos de outros sites (ou de outro programa local em outra porta, ou com um endereço que não seja `127.0.0.1`/`localhost`) recebem `403`, e a recusa fica registrada no `Puxai.log`. Programas fora do navegador, como `curl` e scripts, continuam podendo usar a API normalmente. Detalhes em `rotas/seguranca.py`.

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
| `pasta`     | string | Não         | Subpasta dentro de Downloads (usada nas playlists, com o nome delas) |
| `numero`    | número | Não         | Posição do vídeo na playlist: vai na frente do nome (`03 - Título`) |
| `total`     | número | Não         | Tamanho da playlist, para saber quantos zeros usar no número (`03` de 40, `003` de 150) |

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

**Resposta `400 Bad Request`** quando falta a URL, quando `formato`, `qualidade`, `id` ou o trecho são inválidos, ou quando o link é de uma playlist inteira (`youtube.com/playlist?list=...`). Para baixar uma playlist, liste os vídeos com `GET /api/playlist` e envie um pedido por vídeo, como faz o painel. Um vídeo dentro de uma playlist (`watch?v=...&list=...`) é aceito, e só o vídeo é baixado:

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

Responde `400` para links de playlist e `404` quando o vídeo não é encontrado. Se o link for de um canal ou de outra lista de vídeos sem `list=` no endereço, a resposta é `{"playlist": true, "titulo": "..."}`, e o painel abre a lista de vídeos.

### `GET /api/playlist?url=<link>`

Lista os vídeos de uma playlist (ou de um canal) sem baixar nada, até os primeiros 200. Na página inicial de um canal do YouTube, lista a aba **Vídeos**.

```json
{
  "titulo": "Python Tutorials",
  "canal": "Corey Schafer",
  "site": "YouTube",
  "total": 158,
  "limite": 200,
  "itens": [
    { "numero": 1, "url": "https://www.youtube.com/watch?v=YYXdXT2l-Gg", "titulo": "Python Tutorial for Beginners 1: ...",
      "duracao": "15:29", "miniatura": "https://i.ytimg.com/vi/...", "disponivel": true }
  ]
}
```

`disponivel` é `false` para vídeos privados ou apagados. Responde `400` quando o link não é de uma playlist.

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

### `POST /api/progresso`

O mesmo que a rota acima, para vários downloads de uma vez (o painel usa esta, para não fazer um pedido por vídeo numa playlist). Corpo: `{"ids": ["id1", "id2"]}` (até 500). A resposta tem um objeto por ID, no mesmo formato de `GET /api/progresso/<id>`.

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

### `POST /api/converter/imagem`

Converte uma foto. Envie como `multipart/form-data` o arquivo no campo `arquivo` e o formato de saída no campo `formato`; a resposta é a foto convertida.

| `formato` | Aceita |
|-----------|--------|
| `jpg` (padrão) | HEIC/HEIF |
| `webp` | HEIC/HEIF, JPG e PNG (mantém a transparência) |

```bash
curl -X POST http://127.0.0.1:5000/api/converter/imagem \
  -F "arquivo=@foto.png" -F "formato=webp" -OJ
```

O endereço antigo `POST /api/converter/heic` continua funcionando (sem `formato`, converte para JPG).

| Código | Quando |
|--------|--------|
| `400`  | Nenhum arquivo enviado, formato inválido ou tipo de foto não aceito para esse formato |
| `500`  | Falha na conversão (o arquivo não é uma foto válida) |

### `POST /api/comprimir`

Comprime uma foto (JPG, PNG, WebP ou HEIC). Envie como `multipart/form-data`:

| Campo | Valores |
|-------|---------|
| `arquivo` | a foto |
| `nivel` | `alta`, `equilibrado` (padrão) ou `forte` |
| `tamanho` | maior lado da foto: `original` (padrão), `2560`, `1920` ou `1280` |

A resposta é a foto comprimida. Com `?salvar=1` (usado pelo painel), ela vai para a pasta Downloads e a resposta é um JSON com `arquivo`, `antes` e `depois` (bytes), `largura` e `altura`. Se não der para diminuir sem perder qualidade, a resposta é um JSON com `"ja_otimizada": true` e nada é salvo.

```bash
curl -X POST http://127.0.0.1:5000/api/comprimir \
  -F "arquivo=@foto.jpg" -F "nivel=equilibrado" -F "tamanho=1920" -OJ
```

### `GET /api/historico`

Lista o que o programa já salvou, do mais novo para o mais antigo. Cada item traz `id`, `titulo`, `arquivo`, `caminho`, `tipo` (`video`, `musica` ou `foto`), `formato`, `data` (segundos desde 1970), `origem` (link do vídeo, se houver), `existe` (se o arquivo ainda está lá) e `tamanho` em bytes.

### `DELETE /api/historico/<id>` e `DELETE /api/historico`

Tiram um item da lista, ou limpam a lista toda. Os arquivos continuam na pasta Downloads.

### `POST /api/abrir/<id>`

Abre o arquivo no programa padrão do Windows. Responde `404` se o arquivo foi movido ou apagado. A rota `POST /api/mostrar/<id>` também passa a achar os arquivos do histórico.

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

### `GET /api/preferencias` e `POST /api/preferencias`

Lê ou salva como o programa abre: `{"modo_abertura": "janela"}` ou `{"modo_abertura": "navegador"}`. Vale a partir da próxima vez que o programa abrir.

### `POST /api/abrir-no-navegador` e `POST /api/reabrir-como-aplicativo`

Trocam o modo na hora: a primeira abre o painel no navegador e fecha a janela (o programa continua rodando); a segunda reinicia o programa na janela do aplicativo.

### `GET /api/modo` e `POST /api/focar`

Usadas pela janela do programa: `modo` diz se o painel está na janela própria (`{"janela": true}`) ou no navegador, e `focar` traz a janela para a frente (é o que acontece ao clicar no atalho com o programa já aberto).

## Observações

- O status dos downloads fica em memória: ao fechar o programa, a fila e os status são perdidos.
- O servidor (Waitress) atende só o próprio PC (`127.0.0.1`). Para hospedar num servidor de verdade, use **um único processo**, porque a fila de downloads fica em memória.
- Respeite os termos de uso das plataformas e os direitos autorais do conteúdo baixado.

## Licença

Este projeto está sob a licença MIT. Sinta-se à vontade para usar e modificar.
