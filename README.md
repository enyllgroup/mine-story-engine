# MineStory — Mine-imator

A rota visual escolhida pelo usuário é **Mine-imator**, com personagens,
blocos e texturas Minecraft carregados pelo programa oficial. A narração é
enviada nesta conversa; o próprio modelo ativo do Codex faz a direção visual,
sem API GPT paga e sem substituir seu raciocínio por Llama/Qwen.

**Estado real:** o Mine-imator 2.0.2 oficial para Linux exportou um master nativo
de 600 quadros, 20 segundos, em 1080×1920 a 30 FPS. A versão final tem narração
sintética de 17,949 segundos, legendas por palavra e H.264/AAC. Todos os 539
quadros finais foram decodificados; a sequência e frames em resolução completa
foram inspecionados. Os 87 testes de código passaram. Isso valida esta fixture
técnica, sem concluir o diretor criativo para novas narrações.

O teste atual é **um único vídeo de 17,95 segundos**, com áudio sintético
identificado como teste. O [Sites](https://minestory-arquivos.earlybrook129.chatgpt.site)
publicado contém somente o player e o botão de download desse vídeo, mantendo
o acesso privado do proprietário. Produções anteriores são preservadas, mas não representam aprovação
da aparência Minecraft. O README anterior permanece integralmente em
[docs/LEGACY-BLENDER.md](docs/LEGACY-BLENDER.md).

## Instalação local

Ambiente testado: Debian 13 x86-64, Python 3.12, três CPUs, cerca de 10 GB de RAM,
sem GPU física. O Mine-imator usa Mesa llvmpipe neste host. O pacote oficial
Linux exige X11; `QT_QPA_PLATFORM=offscreen` não funcionou.

```bash
git clone https://github.com/enyllgroup/mine-story-engine.git
cd mine-story-engine
python scripts/install_mineimator.py
python scripts/install_mineimator_x11.py
```

Os scripts baixam os binários oficiais e verificam SHA256 antes de extrair em
`.tools`, sem root. O instalador X11 é específico para bibliotecas Debian 13;
ele não resolve dependências de qualquer distribuição. Requer `dpkg-deb`.
O controlador usa também `xdpyinfo`, ImageMagick `import` e Tkinter do host.
FFmpeg/ffprobe são usados para montagem e inspeção posteriores.

Para gerar o projeto e usar os componentes Python de áudio e legendas:

```bash
python -m venv .venv
.venv/bin/python -m pip install -e .
```

O instalador não ativa ferramentas pagas, baixa modelos locais de direção nem
altera o executável Mine-imator. O download oficial contém os recursos
Minecraft utilizados pelo programa; eles não são redistribuídos neste Git.
A Trial exporta com watermark. A chave Full gratuita é oferecida no
[fluxo oficial de upgrade](https://www.mineimator.com/upgrade), com doação
opcional. Não remover watermark por edição nem modificar o mecanismo de licença.

## Projeto nativo e interface

```bash
.venv/bin/python -m minestory native project --quality final
.venv/bin/python -m minestory native gui start
.venv/bin/python -m minestory native gui status
.venv/bin/python -m minestory native gui screenshot productions/inspecao-001.png
```

O gerador usa `productions/mineimator-validation/test.miproject` na primeira execução
e cria skins/item originais em `assets` dentro desse job. Ele recusa um projeto ou
diretório `assets` já existente. Para outra versão, escolha um diretório novo com
`native project --quality final --output productions/NOVO_JOB/test.miproject`; não
repita a geração sobre a produção anterior. O projeto contém rigs humanos nativos,
keyframes de caminhada e reação, carta extrudada, blocos vanilla e câmera.
Essas intenções devem ser confirmadas no programa e no vídeo exportado.
O teste é uma fixture técnica; não constitui um diretor criativo genérico pronto.

O controlador inicia uma tela `:100` por padrão e recusa substituir uma tela
ativa. Na primeira abertura, confirme visualmente os diálogos iniciais antes de
abrir o arquivo. Para uma sessão existente, informe seu display explicitamente:

```bash
.venv/bin/python -m minestory native gui --display :100 open-project productions/mineimator-validation/test.miproject
.venv/bin/python -m minestory native gui --display :100 screenshot productions/inspecao-002.png
```

Use `click X Y`, `key ctrl+o`, `text` via stdin e `resize WINDOW WIDTH HEIGHT`
após inspecionar as capturas. `text` cola pelo clipboard X11 com Tkinter, mantendo
o proprietário da seleção vivo durante a transferência. Isso evita a perda de
caracteres observada na digitação simulada. Cliques/teclas permanecem pressionados
brevemente para serem recebidos sob carga. O script não presume coordenadas
universais para diálogos nem uma API de renderização inexistente.

Os logs ficam em `.tools/mineimator/runtime`. O log do próprio Mine-imator fica
em `~/Mine-imator/log.txt`. `stop` encerra somente processos iniciados pelo
controlador cuja identidade PID/starttime ainda corresponde ao registro:

```bash
.venv/bin/python -m minestory native gui --display :100 stop
```

## Narração e montagem

O usuário fornece somente seu MP3/WAV nesta conversa. A voz e sua velocidade
devem ser preservadas. Transcrição local e legendas podem reutilizar os módulos
independentes `minestory/audio.py` e `minestory/captions.py`, depois de conferir
as palavras reais. Os timestamps Whisper são estimativas acústicas; não são
forced alignment independente. Nenhum áudio sintético deve ser apresentado como
narração do usuário.

A análise isolada pode ser executada sem acionar o backend visual legado. Use
um diretório de produção novo:

```bash
.venv/bin/python -m minestory analyze entrada/narracao.wav --output productions/NOVO_JOB/transcript.json
```

Existe uma fixture curta opcional, com Piper gratuito e voz `pt_BR-faber-medium`
já verificados em `.tools/piper`. Ela usa dependência de teste
`piper-tts==1.8.0`, não necessária para uma narração enviada pelo usuário:

```bash
.venv/bin/python scripts/generate_mineimator_test_audio.py
```

O script preserva o WAV existente, recusa uma fixture acima de 20 segundos sem
acelerá-la, registra sua origem sintética e gera transcrição/legendas. Em uma
instalação nova, a voz Piper precisa estar disponível com o hash esperado pelo
script; não há download implícito nesse comando.

**Exportação nativa verificada nesta fixture:** use a exportação de animação do próprio
Mine-imator pela interface. Confira câmera ativa, resolução vertical,
30 FPS e intervalo do teste, preservando o projeto anterior antes de alterações.
O gerador usa 1080×1920 e 600 frames em `--quality final`, seu padrão atual.
`--quality preview` gera 540×960. O master 1080×1920 levou 7 min 11 s neste host;
a montagem final levou 41,711 s. Esses tempos não são uma promessa para outros jobs.
O fluxo de cliques foi conduzido com os helpers e inspeção da GUI; o monitor
confirmou log e MP4 reais. O controlador autônomo completo de exportação ainda
não foi exercitado de ponta a ponta no perfil documentado.

Após obter o arquivo nativo, FFmpeg pode acrescentar a narração original e ASS,
produzindo H.264/AAC. Essa montagem não substitui a renderização Mine-imator.
As etapas são acessíveis por `native`; cada comando encaminha seus argumentos
para o script correspondente, sem shell:

```bash
.venv/bin/python -m minestory native project --help
.venv/bin/python -m minestory native gui --help
.venv/bin/python -m minestory native export --help
.venv/bin/python -m minestory native finish --video productions/NOVO_JOB/native.mp4 --audio entrada/narracao.wav --job productions/NOVO_JOB --check-only
# Montagem com limite opcional para disponibilização no Sites:
.venv/bin/python -m minestory native finish --video productions/NOVO_JOB/native.mp4 --audio entrada/narracao.wav --job productions/NOVO_JOB --max-mib 24
```

`finish` exige exportação nativa em1080×1920 a30/60FPS, narração original e
transcrição/legendas compatíveis. `--check-only` apenas verifica essas entradas;
remova-o para a montagem após a exportação real. Etapas indisponíveis retornam
erro; nenhum renderer alternativo é acionado. A integração completa de uma nova
narração com direção, exportação e montagem permanece em andamento.

Os comandos antigos `produce`, `prepare`, `finish`, `render` e `launcher` usam o
pipeline Blender e estão **bloqueados por padrão**. A flag `--legacy-blender`
habilita somente diagnóstico legado explicitamente autorizado; não é o fluxo
de produção da rota atual. Isso inclui `produce --director session`, cujo pacote
de direção pertence ao schema antigo. O teste não exige API paga e não equivale
a uma promessa de produção automática completa a partir de áudio pela CLI.

## Inspeção e limites

Inspecione o arquivo exportado, não apenas o estado da interface:

```bash
ffprobe -v error -show_streams -show_format -of json productions/mineimator-validation/native-1080-best.mp4
ffprobe -v error -show_streams -show_format -of json productions/mineimator-validation/video_final.mp4
```

Abra frames de início, caminhada, coleta/reação, interação e fim. Verifique
enquadramento, texturas, contato com o item, movimento entre frames, duração e
legendas. Detecção técnica de quadros pretos ou estáticos não aprova direção
semântica nem fidelidade visual sozinha. Registre falhas e tempo real de render;
não prometer desempenho de GPU com este hardware.

As skills locais em `.agents/skills` são descobertas pelo Codex. Para esta rota,
use [mineimator-native](.agents/skills/mineimator-native/SKILL.md). As skills
visuais antigas estão marcadas como legadas; seus wrappers Blender não devem ser
executados automaticamente quando chegar uma nova narração. Áudio, legendas e
som são componentes reutilizáveis, sujeitos aos seus contratos e licenças.

Documentação do runtime instalado e evidências:
[docs/MINEIMATOR-RUNTIME.md](docs/MINEIMATOR-RUNTIME.md).
[Resultado e limites do teste](docs/MINEIMATOR-VALIDATION.md).
Documentação Blender anterior permanece apenas para histórico e diagnóstico.
