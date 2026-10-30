---
name: minecraft-world-builder
description: "Construir ambientes em blocos com a engine Blender MineStory. Usar ao criar paisagens, vilas, laboratórios e outros lugares no storyboard estruturado."
---

> **Rota visual legada (Blender):** o procedimento abaixo não deve ser executado
> automaticamente para novas narrações da rota Mine-imator. Use
> [mineimator-native](../mineimator-native/SKILL.md) e os projetos nativos.
> Este wrapper não constitui uma integração Mine-imator.

Adicionar blocos explícitos em `blocks` e escolher o ambiente que sustenta a narração. Usar coordenadas z-up, grade de um bloco, texturas pixeladas nearest e iluminação simples. Não importar assets Mojang sem direitos nem instalar mods para esta operação. Executar `scripts/run.py STORYBOARD --audio AUDIO --quality preview --output DIRETORIO` para construir e renderizar as cenas reais. Rever a folha de contato; corrigir só as cenas afetadas.

Executar o script com `--help` para argumentos. O wrapper usa a `.venv` do repositório e não instala dependências. Todos os subprocessos recebem listas de argumentos, sem interpolação em shell.
