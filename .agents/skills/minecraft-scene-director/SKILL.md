---
name: minecraft-scene-director
description: "Executar o grafo temporal de cenas MineStory em Blender. Usar para sincronizar acontecimentos, dependências entre objetos e renderização por cena."
---

Validar os limites de cada cena e referências de atores/props. Usar início/fim globais na cena e tempos relativos em ações e animações. Executar `scripts/run.py STORYBOARD --audio AUDIO --quality preview --output DIRETORIO`; o renderizador transforma o JSON em geometria e keyframes reais. Conservar produções anteriores e aproveitar o cache por conteúdo. Rever eventos próximos aos cortes; não declarar animação validada pelo JSON sozinho.

Executar o script com `--help` para argumentos. O wrapper usa a `.venv` do repositório e não instala dependências. Todos os subprocessos recebem listas de argumentos, sem interpolação em shell.
