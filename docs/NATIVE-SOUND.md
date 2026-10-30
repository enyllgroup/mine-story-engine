# Sons nativos e identidade sonora permanente

O fluxo atual prefere sons Minecraft reais para ações vanilla e efeitos
procedurais originais para acontecimentos sem equivalente no jogo. A narração
original define a duração. O tema de um vídeo não é salvo como regra permanente.

## Fontes verificadas

Em 30/10/2026 foram consultados os sites oficiais:

- [Minecraft Usage Guidelines](https://www.minecraft.net/en-us/usage-guidelines).
- [EULA](https://www.minecraft.net/en-us/eula).
- [Manifesto de versões Mojang](https://piston-meta.mojang.com/mc/game/version_manifest_v2.json).
- [Índice 8 de Minecraft 1.20.2](https://piston-meta.mojang.com/v1/packages/29fd6442259e3901f1a62fbdb696d14137b30f3a/8.json).

O catálogo contém 18 eventos/27 OGGs, 370.457 bytes: passos em grama/pedra, coleta de
item, baú, botão, experiência, levelup, portal, teleporte, explosão, vidro, água,
fogo e pistão. Somente esse pequeno subconjunto é baixado do servidor oficial
`resources.download.minecraft.net`, com SHA1 e tamanho fixos. Não é necessário
baixar launcher, cliente do jogo ou um pacote de terceiros.

Os direitos permanecem com Mojang/Microsoft. As Guidelines definem assets como
incluindo “sounds and other audio” e permitem vídeos com conteúdo/comentário
original, gratuitos para assistir, inclusive com publicidade sob suas condições.
Isso não é uma licença CC0, aprovação específica deste canal ou autorização para
redistribuir os arquivos do jogo isoladamente. O manifesto local registra essa
base e os links. Não há música Minecraft neste catálogo. Os OGGs permanecem
apenas em `library/audio/minecraft/1.20.2/`, ignorada pelo Git; somente o mix do
vídeo deve acompanhar sua produção.

## Operação

```bash
.venv/bin/python scripts/native_sound_design.py install
.venv/bin/python scripts/native_sound_design.py verify
.venv/bin/python scripts/native_sound_design.py list
```

Cada produção guarda `sound_cues.json`, `effects.wav`, `effects.sound.json`,
`audio_mix.wav` e `audio_mix.sound.json` dentro de seu diretório próprio.
Formato de cues, sem determinar um roteiro fixo:

```json
{
  "duration": 12.0,
  "events": [
    {"event":"minecraft:footstep_grass","at":0.4,"gain":0.25,"pan":-0.2},
    {"event":"original:scan","at":3.1,"gain":0.22},
    {"event":"minecraft:portal_ambient","at":6.0,"duration":4.0,"gain":0.12}
  ]
}
```

```bash
.venv/bin/python scripts/native_sound_design.py timeline productions/NOVO_JOB/sound_cues.json --output productions/NOVO_JOB/effects.wav
.venv/bin/python scripts/native_sound_design.py mix --narration productions/NOVO_JOB/input/narracao.wav --effects productions/NOVO_JOB/effects.wav --output productions/NOVO_JOB/audio_mix.wav
```

O mixer aplica pan estéreo, loops explícitos, variantes e ducking sob a voz.
Não modifica velocidade/pitch, não sintetiza fala e mantém o SHA256 da narração
original. O limiter 0,98 controla a soma. A transcrição deve continuar vinculada
ao áudio original; a mixagem é derivada. Arquivos de produção existentes são
recusados, incluindo efeitos e relatórios.

Os quatro eventos científicos originais são `original:digitalize`,
`original:squeeze`, `original:scan` e `original:whoosh`. Essas formas de onda
são criadas pelo código, rotuladas CC0 e nunca identificadas como sons Mojang.
O Codex escolhe os eventos pela atuação e pelos contatos físicos da cena.

## Validação executada

```bash
.venv/bin/python -m pytest tests/test_native_sound.py -q
```

Seis testes verificam proveniência, SHA, recusa de assets corrompidos, nomes/tempos
inválidos, preservação de arquivos e mixagem real FFmpeg sem retiming. O
instalador foi executado e todos os 27 arquivos tiveram seus SHA1 conferidos.
Isso comprova a integração sonora; qualidade editorial e sincronismo de uma
história específica ainda exigem inspeção do vídeo dessa produção.

O smoke test privado `productions/audio-integration-smoke-v001` também decodificou
os 27 OGGs oficiais e misturou seis cues vanilla/originais sobre um tom de teste
sintético de sete segundos. Não usou nem alterou a narração do usuário. O mix
resultou em 336.000 amostras por canal a 48 kHz, sem mudança de duração.

## Finalização com a voz original e efeitos

O finalizador nativo aceita efeitos como entrada separada:

```bash
.venv/bin/python scripts/finish_mineimator.py --video productions/NOVO_JOB/native.mp4 --audio productions/NOVO_JOB/input/narracao.wav --effects productions/NOVO_JOB/effects.wav --job productions/NOVO_JOB --quality preview
```

`--audio` continua sendo o arquivo original vinculado ao transcript. O programa
recusa uma mixagem passada em seu lugar e também recusa duplicar a narração como
`--effects`. Os FX precisam cobrir a duração real do áudio; a timeline pode conter
silêncio entre acontecimentos. O mix derivado é criado apenas dentro do diretório
de trabalho da finalização e sua proveniência é incluída nos relatórios.

O padrão `--quality final` exige 1080×1920 e preserva os nomes `video_final.mp4`,
`finish_report.json`, `qc_report.json` e `contact_sheet.jpg`. A opção `preview`
exige 540×960 nativo, sem upscale, e salva `video_preview.mp4`,
`finish_preview_report.json`, `qc_preview_report.json` e
`preview_contact_sheet.jpg`. Ambos mantêm 30/60 FPS do arquivo nativo e a duração
da voz; não existe limite artificial de 20 segundos neste estágio de montagem.

Quatro testes em `tests/test_native_finish.py` verificam os novos controles,
incluindo FFmpeg real com um pequeno fixture sintético de decodificação,
mixagem sem retiming, proteção dos arquivos e vínculo ao áudio original. Esse
fixture técnico não é apresentado como uma renderização Minecraft.
