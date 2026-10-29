---
name: narration-analyzer
description: "Transcrever e alinhar narração PT-BR sem modificar a voz. Usar ao receber MP3/WAV ou investigar timestamps e pausas."
---

Executar `scripts/run.py AUDIO --output DIRETORIO` para obter transcrição e duração reais. Usar Whisper local, sem API paga. Preservar cada palavra falada; não substituir a voz nem criar timestamps sintéticos. Inspecionar `transcript.json`, probabilidades e avisos antes de dirigir cenas. Consultar `minestory/audio.py` para o backend e cache.

Executar o script com `--help` para argumentos. O wrapper usa a `.venv` do repositório e não instala dependências. Todos os subprocessos recebem listas de argumentos, sem interpolação em shell.
