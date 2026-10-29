# Validação executada

Este documento separa resultados reais de limitações. Áudios em `examples/audio/*SINTETICO.wav` foram criados **exclusivamente para testar a engine**; não são narração do usuário. A entrada do usuário na produção será somente o áudio anexado na conversa.

## Ambiente

Linux x86-64, 3 CPUs Intel Xeon 8573C, cerca de 10 GB de RAM, sem GPU exposta. Blender 4.3.2 com Workbench e render EGL software; FFmpeg 7.1.5 com libass/libx264; Python 3.12.14. Ferramentas do sistema já estavam instaladas. `.venv` isolada com dependências, incluindo faster-whisper 1.2.1 e PyAV 16.1.0. Versões resolvidas em `requirements.lock`; versões efetivamente instaladas em `environment-versions.json`.

## Testes obrigatórios

| Teste | Evidência executada | Resultado/limite |
|---|---|---|
| A — personagem |120 frames renderizados; walking, pickup, reação, contato visual; sequência completa cartas | Proporções Minecraft, articulação e movimentos reais. Entrega entre personagens funciona como aproximação por constraints/trajetória; contato preciso de mãos e orientação ainda precisam refinamento. |
| B — cenário | Construção procedural de terreno, caminho, casas, árvores, baú, bancada; revisão com bancas de feira e chão estendido | Frames efetivamente renderizados; não é um cenário descrito apenas em JSON. |
| C — objeto novo | Carta editorial original feita de cuboides; cartas gastas, lupa, troféu e proteção personalizados | Atores seguram/apontam/entregam; sem arte de marca ou personagem de terceiros. `.bbmodel` gerado, mas GUI Blockbench não foi instalada/testada. |
| D — sincronização | Fixture Piper com frases e pausas conhecidas; transcrição real; MP4 sincronia_preview de 8,344 s com ação nos tempos caiu/encontrou/desapareceu | QC técnico passou. Recorte acústico removeu invasão nas pausas medidas. Persistem erros de reconhecimento textual; não se afirma precisão fonética independente. |
| E — dois assuntos | Planos individualmente criados pelo Codex para cartas e desaparecimento do Sol; preflights 3D reais | Cartas: procura, raridade, conservação, verificação, lances e memória. Sol: luz em trânsito, apagão, trajetória, Lua, calor, plantas e geotermia. Recursos e acontecimentos são diferentes. |
| F — vídeo >60 s | `productions/cartas_final/video_final.mp4`: 70,466667 s, **1080×1920 nativo**, 30 FPS, H.264/AAC | MP4 completo renderizado e reinspecionado. Áudio: 70,460952 s; erro de duração: 0,005715 s. QC técnico passou sem ocorrências; 12 cenas. Exportação de 21.061.495 bytes, também em `examples/results/cartas_final.mp4`. |

Os planos desses testes são fixtures em `examples/direction_*.json`. Não são o diretor geral nem templates obrigatórios para novas narrações. A etapa criativa das novas produções ocorre no modelo ativo do Codex, lendo os beats reais do áudio enviado.

Vídeos exportados e relatórios estão também em `examples/results/`. A revisão do Sol (`sol_review_preview.mp4`) corrigiu a sobreposição das duas Terras e substituiu a cena em que o observador escondia a planta. Na revisão, **5 de 7 cenas vieram do cache** e somente 2 foram renderizadas; o relatório mediu 113,795 s no host simultaneamente ocupado pelo render nativo.

## Inspeção visual

A primeira prévia mostrou borda do terreno no rodapé e uma associação incorreta do material ouro à textura de carta. A revisão posterior ampliou o chão, corrigiu o material e diferenciou feira/vila/caverna; a prévia anterior foi preservada. Preflight mediu cinco poses por cena e corrigiu 10 enquadramentos para manter o assunto acima da legenda.

Frames reais de atuação, carta, baú, casas, bancada, entrega e planetas foram abertos e inspecionados. Depois da exportação nativa completa, o MP4 foi novamente decodificado e medido. Sua folha de contato e quadros extraídos em resolução final, incluindo texto e transferência do objeto, foram inspecionados. Não foram encontradas falhas nos gates técnicos. Isso não substitui revisão editorial de uma nova narração. Veja [relatório de render](RENDER-VALIDATION.md).

## Áudio e legendas

Comparação no mesmo WAV Piper: cartas com 204 palavras, WER small 8,82% e turbo 1,96%; Sol com 115 palavras, small 4,35% e turbo 0,87%. Turbo tornou-se padrão. Restam erros como preço/peso e comprar/contar no teste sintético. Não foram escondidos usando o roteiro desejado. Dados, tempos e reprodução em [AUDIO-VALIDATION.md](AUDIO-VALIDATION.md).

ASS por palavra ativa e SRT gerados da transcrição reconhecida. Fonte Pixelify Sans com OFL, contorno e margem conservadora para interface. É preciso conferir a legenda de uma narração real antes de chamá-la de editorialmente pronta. Música off; sons originais baixos e ducking. Não há mudança de velocidade da voz.

Foi medida a correlação entre a narração original e o áudio AAC realmente decodificado do MP4 em 5 janelas de 2 s (1, 15, 30, 45 e 65 s). Pico de correlação em **0 amostras de atraso** nas 5 janelas; coeficientes de 0,99984 a 0,99999. Isso apoia preservação do relógio/voz, sem provar precisão fonética das legendas nem substituir escuta artística dos efeitos. Dados em [audio-mix-validation.json](audio-mix-validation.json).

## Desempenho e armazenamento medidos

A produção nativa completa, incluindo preflight, render, montagem, legendas, som e QC, levou **1.665,131 s (27 min 45 s)**. Havia outras produções/testes concorrentes durante parte do trabalho; os tempos por cena variaram. A prévia completa original levou 263,433 s. São medições deste host, sem GPU.

A compactação real de 34 caches concluídos removeu 6.015 PNGs intermediários e liberou **15.682.658.505 bytes**, preservando MP4s verificados, projetos Blender, metadados e três quadros de referência por cena. O SHA256 do vídeo final permaneceu igual. Caches incompletos não são compactados. Evidência: `cache-compaction-validation.json`.

A biblioteca foi exercitada com texturas, modelos, rigs, animações, câmeras, cenários, iluminação, transições de corte e efeitos sonoros reais. Seu teste confirma que uma segunda produção reutiliza os mesmos hashes e preserva o conteúdo anterior.

## Limitações reais

- Fidelidade visual reconhecível como linguagem Minecraft, com texturas originais. Não reproduz exatamente recursos/iluminação do cliente vanilla.
- Não existe render backend Minecraft Java, exportador Mine-imator ou MCP Blockbench instalado. Foram pesquisados e comparados; não foram declarados como integrações executadas.
- Diretor pela conversa exige uma sessão ativa do Codex. O comando externo Codex CLI retornou 401 neste ambiente; não é um serviço autônomo hospedado 24 h. O usuário continua fornecendo só áudio aqui.
- Modelo local opcional Qwen 1.5B é uma alternativa inferior de offline, não o padrão. `llama.cpp` é seu runtime. Disponibilidade HTTP foi verificada; uma produção completa com esse diretor não foi certificada.
- Não há forced alignment CTC independente nem garantia de transcrição sem erros.
- Noite e iluminação são aproximações do Workbench; exposição não produziu uma mudança de dia/noite convincente no enquadramento observado. Atuação/contato de mãos têm aproximações. A primeira demonstração repete o ambiente de feira em 11 de 12 cenas.
- QC por amostras pode perder defeitos entre frames. Projeção não detecta oclusões; não há OCR/validador semântico automático completo. O Codex precisa inspecionar a produção.
- Não há geração automática de esqueletos arbitrários, simulação de física universal ou importação completa de meshes/IK/Molang.
- Transições nativas são cortes diretos. Reações geram partículas quadradas; novos efeitos/transições precisam ser construídos com props animados. Recursos não implementados são recusados em vez de silenciosamente ignorados.
- Render nativo 1080 sem GPU é substancialmente mais lento que a prévia. Cache e retomada funcionam; não se promete produção em tempo real neste hardware.
- Launcher Tk implementado, mas não validado com interface gráfica neste servidor.

## Repetir verificações

```bash
.venv/bin/python -m pytest -q
.venv/bin/python scripts/validate_audio_fixtures.py --help
.venv/bin/python -m minestory doctor
.venv/bin/python -m minestory qc productions/cartas_preview/video_preview.mp4 --transcript productions/cartas_preview/transcript.json --storyboard productions/cartas_preview/storyboard.json --output productions/cartas_preview/reinspection
```

Os testes de guardas usam áudio PCM/FFmpeg e QC reais; os testes unitários de sessão substituem somente ASR para testar invariantes sem baixar modelos novamente. Eles não são usados como evidência de inferência real, que foi medida separadamente.

A instalação por `requirements.lock` foi repetida em outra virtualenv **sem system-site-packages**: instalação editável, importação do transcritor e todos os 46 testes então existentes passaram. Depois das guardas adicionais e dos testes de biblioteca/compactação, a suíte final passou com **53 testes**. O modelo e a transcrição existentes também foram lidos pelo ambiente novo, com cache confirmado. A guarda de custo recusa autenticação por API paga no Codex externo; a produção pela conversa não inicia outra chamada de modelo.
