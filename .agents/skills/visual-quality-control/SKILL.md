---
name: visual-quality-control
description: "Inspecionar MP4 realmente renderizado com ffprobe, frames e análise de tempos. Usar ao validar exportação, investigar quadros pretos, travamentos e qualidade."
---

Executar `scripts/run.py VIDEO --storyboard STORYBOARD --transcript TRANSCRIPT --output DIRETORIO`. Abrir a folha de contato e frames de ações críticas, conferir objetos e legendas e ouvir trechos com efeitos. Tratar `technical_pass` apenas como aprovação dos testes técnicos implementados; coerência semântica e fidelidade vanilla exigem inspeção visual. Usar `affected_scenes` para concentrar correções. Nunca inventar uma aprovação global a partir do probe.

Executar o script com `--help` para argumentos. O wrapper usa a `.venv` do repositório e não instala dependências. Todos os subprocessos recebem listas de argumentos, sem interpolação em shell.
