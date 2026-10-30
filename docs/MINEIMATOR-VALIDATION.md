# Validação nativa — 30/10/2026

O Mine-imator **2.0.2 oficial para Linux**, sem alteração do executável,
renderizou a cena Minecraft. A versão Full foi ativada pelo fluxo gratuito
oficial com doação opcional. Nenhuma API paga ou renderer alternativo participou.

O único vídeo disponibilizado está no
[Sites MineStory](https://minestory-arquivos.earlybrook129.chatgpt.site), com player
e download, mantendo o acesso privado do proprietário. Os artefatos locais ficam
em `productions/mineimator-validation/`, excluídos do Git. Produções antigas
foram preservadas e retiradas da interface publicada.

## Resultado medido

| Item | Resultado |
| --- | --- |
| Master Mine-imator | 1080×1920, 30 FPS, H.264, 600 quadros, 20,000 s |
| Exportação nativa | 00:26:10–00:33:21 UTC: **431 s** |
| Master em disco | 59.321.278 bytes |
| Narração | Piper PT-BR, fixture sintética CC0, **17,949025 s**, sem retiming |
| Legendas | 57 palavras; 61 eventos ASS; SRT editável |
| Montagem final | H.264/yuv420p e AAC, 1080×1920/30 FPS, 539 quadros |
| Duração final | Vídeo 17,966667 s; áudio 17,949 s; diferença inferior a um quadro |
| Arquivo final | **20.375.810 bytes**, abaixo do limite configurado de 24 MiB |
| Tempo de montagem/QC | 41,711 s |
| Testes de código | **87 passaram** |

Hardware: Debian 13 x86-64, três CPUs, cerca de 10 GB de RAM, sem GPU física;
OpenGL usa Mesa llvmpipe. Os tempos são desta execução, não uma garantia para
outros computadores ou produções.

SHA256 do master: `6480f5fae644883e90c994ae7332f09eb3dbb912e1e3e4e83fa88afa1d7cbb14`.

SHA256 do vídeo final: `7afd25f7b6686d6edc5cd488fc2694faf0802ed6cf63caf5f061304ef61763a6`.

## Evidências e inspeção

O log nativo registra o destino exato, MP4, preset Best, 30 FPS, 1080×1920,
renderização de alta qualidade e `Movie exporting finished!`. O controlador foi
executado em `--monitor` e confirmou esses dados com `ffprobe` e a contagem de
600 quadros. A exportação foi conduzida com os helpers e inspeção da GUI real.
O fluxo completo de cliques do controlador autônomo permanece sem teste de
ponta a ponta; testes de guardas e OCR não substituem essa validação.

Todos os 539 quadros finais foram decodificados, sem quadros pretos detectados.
A análise de movimento a 2 FPS, fora da faixa das legendas, não encontrou trechos
estáticos de três segundos. O Codex inspecionou `contact_sheet.jpg`, a imagem
nativa `native-frame-299.png` e os frames finais completos em 7,6 e 13,5 segundos.

Foram observados personagens articulados caminhando, inclinação para a carta,
item personalizado acompanhando a mão, reação, entrada do segundo personagem,
oferta de esmeralda, texturas presentes e legendas legíveis abaixo dos atores.
Os relatórios automáticos mantêm `needs_visual_review`; `visual_review.json`
registra a inspeção posterior e seu escopo técnico limitado.

Relatórios locais: `native_export_report.json`, `native_application.log`,
`finish_report.json`, `qc_report.json`, `visual_review.json` e
`production_report.json`.

## Reproduzir e diagnosticar

Use os instaladores, o gerador e a GUI descritos no [README](../README.md).
Escolha um diretório novo para preservar produções anteriores. Após a exportação
nativa, com transcrição e ASS correspondentes ao áudio:

```bash
.venv/bin/python -m minestory native finish --video productions/NOVO_JOB/native.mp4 --audio entrada/narracao.wav --job productions/NOVO_JOB --max-mib 24
.venv/bin/python -m pytest -q
ffprobe -v error -show_streams -show_format -of json productions/NOVO_JOB/video_final.mp4
```

O limite de tamanho usa CRF18 com VBV e verifica os bytes reais antes de publicar
o arquivo. Não faz upscale, altera FPS ou acelera a voz. Falhas preservam os
temporários e não aprovam um MP4 parcial. Consulte os logs antes de repetir.

## Limites reais

- Esta é uma fixture técnica de animação, **não a engine completa para qualquer
  narração**. Compilação criativa arbitrária, biblioteca de atuação nativa e
  exportação autônoma completa continuam em integração.
- A introdução não representa literalmente milhares de cartas comuns. Não há
  aprovação editorial completa da correspondência entre todas as frases e cenas.
- O levantamento usa troca de visibilidade entre item no chão e na mão; não há
  IK de pegada nem simulação física. Este teste não inclui efeitos sonoros.
- Os tempos de palavra vieram do Whisper-small com estimativas acústicas, sem
  forced alignment independente. Três erros ortográficos da fixture controlada
  foram corrigidos; a transcrição bruta e o registro foram preservados.
- O master usou ID textual de câmera e gerou duas mensagens `ToInt` no
  carregamento, sem falha de exportação. A revisão do gerador para câmera `-5`
  foi auditada no fonte, mas não recarregada após o render.
- Os testes antigos de dois assuntos e duração acima de 60 s não foram repetidos:
  a instrução atual autorizou um único vídeo curto. A narração sintética nunca
  deve ser apresentada como a narração real do usuário.

O teste comprova que a rota Mine-imator é executável neste ambiente. A ausência
de erros técnicos não equivale à aprovação estética do usuário nem a cumprir
todos os critérios originais de uma engine criativa autônoma.
