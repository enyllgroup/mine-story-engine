---
name: render-pipeline
description: "Produzir vídeo vertical MineStory desde um único arquivo de áudio. Usar para render completo, prévia, legendas, cache, relatório e exportação MP4."
---

Quando o usuário anexar a narração nesta conversa, seguir `visual-director`: `python -m minestory prepare AUDIO`, criar o plano com o próprio Codex e `python -m minestory finish JOB --quality preview`. Nenhuma segunda autenticação ou API é necessária; o áudio é a única entrada do usuário. Para execução externa com Codex CLI autenticado, executar `scripts/run.py AUDIO --quality preview`; usar `--quality final` para 1080×1920 nativo. O áudio é a referência absoluta de duração. Consultar o relatório e QC antes de entregar. Não sobrescrever produções anteriores, não inserir abertura ou encerramento artificial e não alterar velocidade da narração. Diagnosticar o estágio com erro e retomar o job pelo mecanismo documentado na CLI.

Executar o script com `--help` para argumentos. O wrapper usa a `.venv` do repositório e não instala dependências. Todos os subprocessos recebem listas de argumentos, sem interpolação em shell.
