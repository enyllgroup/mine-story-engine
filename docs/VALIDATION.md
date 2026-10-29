# Validação executada

Este documento separa resultados reais de limitações. Áudios em `examples/audio/*SINTETICO.wav` foram criados **exclusivamente para testar a engine**; não são narração do usuário. A entrada do usuário na produção será somente o áudio anexado na conversa.

## Ambiente

Linuxx86-64,3CPUs Intel Xeon8573C,~10GBRAM,sem GPU exposta. Blender4.3.2 com Workbench e render EGL software; FFmpeg7.1.5 com libass/libx264; Python3.12.14. Ferramentas do sistema já estavam instaladas. `.venv` isolada com dependências, incluindo faster-whisper1.2.1 e PyAV16.1.0. Versões resolvidas em `requirements.lock`.

## Testes obrigatórios

| Teste | Evidência executada | Resultado/limite |
|---|---|---|
| A — personagem |120frames renderizados; walking, pickup, reação, contato visual; sequência completa cartas | Proporções Minecraft, articulação e movimentos reais. Entrega entre personagens funciona como aproximação por constraints/trajetória; contato preciso de mãos e orientação ainda precisam refinamento. |
| B — cenário | Construção procedural de terreno, caminho, casas, árvores, baú, bancada; revisão com bancas de feira e chão estendido | Frames efetivamente renderizados; não é um cenário descrito apenas em JSON. |
| C — objeto novo | Carta editorial original feita de cuboides; cartas gastas, lupa, troféu e proteção personalizados | Atores seguram/apontam/entregam; sem arte de marca ou personagem de terceiros. `.bbmodel` gerado, mas GUI Blockbench não foi instalada/testada. |
| D — sincronização | Fixture Piper com frases e pausas conhecidas; transcrição real; MP4sincronia_preview8,344s com ação nos tempos caiu/encontrou/desapareceu | QC técnico passou. Recorte acústico removeu invasão nas pausas medidas. Persistem erros de reconhecimento textual; não se afirma precisão fonética independente. |
| E — dois assuntos | Planos individualmente criados pelo Codex para cartas e desaparecimento do Sol; preflights3D reais | Cartas: procura, raridade, conservação, verificação, lances e memória. Sol: luz em trânsito, apagão, trajetória, Lua, calor, plantas e geotermia. Recursos e acontecimentos são diferentes. |
| F — vídeo>60s | `productions/cartas_preview/video_preview.mp4`,70,466667s,360×640,30FPS,H.264/AAC | MP4 completo renderizado e inspecionado. Duração áudio70,460952s,erro0,005715s. QC técnico passou;12cenas. Versão final1080×1920 em validação separada; consultar relatório real antes de afirmar conclusão. |

Os planos desses testes são fixtures em `examples/direction_*.json`. Não são o diretor geral nem templates obrigatórios para novas narrações. A etapa criativa das novas produções ocorre no modelo ativo do Codex, lendo os beats reais do áudio enviado.

## Inspeção visual

A primeira prévia mostrou borda do terreno no rodapé e uma associação incorreta do material ouro à textura de carta. A revisão posterior ampliou o chão, corrigiu o material e diferenciou feira/vila/caverna; a prévia anterior foi preservada. Preflight mediu cinco poses por cena e corrigiu10enquadramentos para manter o assunto acima da legenda.

Frames reais de atuação, carta, baú, casas, bancada, entrega e planetas foram abertos e inspecionados. O frame nativo1080×1920 foi inspecionado; isso não deve ser confundido com validação de um MP4final completo. Veja [relatório de render](RENDER-VALIDATION.md) e os relatórios de cada produção.

## Áudio e legendas

Comparação no mesmo WAVPiper: cartas204palavras,smallWER8,82%,turbo1,96%; Sol115palavras,small4,35%,turbo0,87%. Turbo tornou-se padrão. Restam erros como preço/peso e comprar/contar no teste sintético. Não foram escondidos usando o roteiro desejado. Dados, tempos e reprodução em [AUDIO-VALIDATION.md](AUDIO-VALIDATION.md).

ASS por palavra ativa e SRT gerados da transcrição reconhecida. Fonte PixelifySans comOFL, contorno e margem conservadora para interface. É preciso conferir a legenda de uma narração real antes de chamá-la de editorialmente pronta. Música off; sons originais baixos e ducking. Não há mudança de velocidade da voz.

## Limitações reais

- Fidelidade visual reconhecível como linguagem Minecraft, com texturas originais. Não reproduz exatamente recursos/iluminação do cliente vanilla.
- Não existe render backend MinecraftJava, exportadorMine-imator ou MCPBlockbench instalado. Foram pesquisados e comparados; não foram declarados como integrações executadas.
- Diretor pela conversa exige uma sessão ativa do Codex. O comando externo CodexCLI retornou401neste ambiente; não é um serviço autônomo hospedado24h. O usuário continua fornecendo só áudio aqui.
- Modelo local opcionalQwen1.5B é uma alternativa inferior de offline, não o padrão. `llama.cpp` é seu runtime. DisponibilidadeHTTP foi verificada; uma produção completa com esse diretor não foi certificada.
- Não há forced alignmentCTCindependente nem garantia de transcrição sem erros.
- Noite e iluminação são aproximações doWorkbench; exposição não produziu uma mudança de dia/noite convincente no enquadramento observado. Atuação/contato de mãos têm aproximações. A primeira demonstração repete o ambiente de feira em11de12cenas.
- QC por amostras pode perder defeitos entre frames. Projeção não detecta oclusões; não há OCR/validador semântico automático completo. O Codex precisa inspecionar a produção.
- Não há geração automática de esqueletos arbitrários, simulação de física universal ou importação completa de meshes/IK/Molang.
- Render nativo1080sem GPU é substancialmente mais lento que a prévia. Cache e retomada funcionam; não se promete produção em tempo real neste hardware.
- LauncherTk implementado, mas não validado com interface gráfica neste servidor.

## Repetir verificações

```bash
.venv/bin/python -m pytest -q
.venv/bin/python scripts/validate_audio_fixtures.py --help
.venv/bin/python -m minestory doctor
.venv/bin/python -m minestory qc productions/cartas_preview/video_preview.mp4 --transcript productions/cartas_preview/transcript.json --storyboard productions/cartas_preview/storyboard.json --output productions/cartas_preview/reinspection
```

Os testes de guardas usam áudioPCM/FFmpeg e QC reais; os testes unitários de sessão substituem somenteASRpara testar invariantes sem baixar modelos novamente. Eles não são usados como evidência de inferência real, que foi medida separadamente.
