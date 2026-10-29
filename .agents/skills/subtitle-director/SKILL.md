---
name: subtitle-director
description: "Exportar legendas SRT e ASS com destaque palavra a palavra em PT-BR. Usar para legendar transcrição alinhada e ajustar safe zones, tamanho ou fonte."
---

Executar `scripts/run.py TRANSCRIPT --output DIRETORIO` para gerar `legendas.srt` e `legendas.ass`. Usar palavras reais e timestamps do áudio, sem resumo ou acréscimos. Manter grupos curtos, alto contraste e destaque amarelo, com zona segura para botões e rodapé. A fonte Pixelify Sans deve estar disponível com sua licença. O ASS é editável; a montagem final grava suas legendas no vídeo. Inspecionar legibilidade em frames de prévia.

Executar o script com `--help` para argumentos. O wrapper usa a `.venv` do repositório e não instala dependências. Todos os subprocessos recebem listas de argumentos, sem interpolação em shell.
