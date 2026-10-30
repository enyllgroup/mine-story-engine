---
name: sound-designer
description: "Sincronizar SFX vanilla Minecraft com ações nativas Mine-imator, usar efeitos originais adequados para fenômenos novos e mixar sob a narração preservada."
---

## Rota atual nativa

Priorize sons **reais do Minecraft** para acontecimentos vanilla. O catálogo
versionado está em `assets/audio/minecraft-sfx-1.20.2.json`; os OGGs oficiais
baixados ficam somente na biblioteca local ignorada pelo Git. Não incluir
OGGs, cache, narrações ou mixagens no código publicado. Não apresentar os sons
Minecraft como CC0: Mojang/Microsoft mantêm os direitos; a utilização segue as
[Usage Guidelines](https://www.minecraft.net/en-us/usage-guidelines).

```bash
.venv/bin/python scripts/native_sound_design.py install
.venv/bin/python scripts/native_sound_design.py verify
.venv/bin/python scripts/native_sound_design.py list
.venv/bin/python scripts/native_sound_design.py timeline productions/NOVO_JOB/sound_cues.json --output productions/NOVO_JOB/effects.wav
.venv/bin/python scripts/native_sound_design.py mix --narration productions/NOVO_JOB/input/narracao.wav --effects productions/NOVO_JOB/effects.wav --output productions/NOVO_JOB/audio_mix.wav
```

Cada cue contém `event`, `at` em segundos globais, `gain` opcional 0–1 e
`pan` opcional -1–1. `duration` repete o som para ambientes; `variant` escolhe
uma das gravações originais. Use nomes retornados por `list`; não inventar IDs.
O JSON contém a duração real da narração em `duration` e uma lista `events`.
O Codex deve criar os cues a partir das **ações reais**, não de palavras isoladas.
Sincronize o passo com contato do pé, o impacto com contato físico e o portal
com abertura/travessia. Cues e decisões da história vivem somente na produção;
a política e o catálogo são permanentes. Consulte `docs/NATIVE-SOUND.md`.

Para conceitos sem equivalente vanilla, prefira eventos `original:*` próprios
(`digitalize`, `squeeze`, `scan`, `whoosh`), rotulados CC0. Não baixar áudio de
Pokémon ou músicas de terceiros sem autorização/licença aplicável. Música off.
Efeitos discretos, com ducking sob a voz. A mixagem tem ganho nominal da voz 1,
sem alteração de velocidade/pitch; registra o SHA256 da narração original e
um limiter 0,98 protege a soma. Resampling/mapeamento de canais não é retiming.

Não sobrescrever produções existentes. Não substituir o SHA do áudio original
no transcript pelo SHA da mixagem derivada. A finalização deve conferir essa
cadeia de proveniência.

O wrapper antigo `scripts/run.py STORYBOARD --audio NARRACAO --output DIRETORIO`
continua disponível para diagnósticos com efeitos exclusivamente procedurais;
ele não representa seleção dos sons vanilla nem deve substituí-los silenciosamente.

Executar o script com `--help` para argumentos. O wrapper usa a `.venv` do repositório e não instala dependências. Todos os subprocessos recebem listas de argumentos, sem interpolação em shell.
