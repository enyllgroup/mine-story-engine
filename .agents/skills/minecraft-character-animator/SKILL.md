---
name: minecraft-character-animator
description: "Dirigir atuação de personagens em blocos com pivôs proporcionais ao Minecraft. Usar para caminhar, correr, olhar, reagir, segurar e entregar itens."
---

> **Rota visual legada (Blender):** o procedimento abaixo não deve ser executado
> automaticamente para novas narrações da rota Mine-imator. Use
> [mineimator-native](../mineimator-native/SKILL.md) e os projetos nativos.
> Este wrapper não constitui uma integração Mine-imator.

Compor `actors[].actions` com os tipos validados em `scene_schema.ACTIONS`; definir tempos relativos à cena e referenciar objetos existentes. Usar andar, apontar e reação para comunicar causa e consequência, evitando repouso longo. A engine reutiliza pivôs para cabeça, tronco e membros. Executar `scripts/run.py STORYBOARD --audio AUDIO --quality preview --output DIRETORIO` e inspecionar movimento real, contato com o item e orientação.

Executar o script com `--help` para argumentos. O wrapper usa a `.venv` do repositório e não instala dependências. Todos os subprocessos recebem listas de argumentos, sem interpolação em shell.
