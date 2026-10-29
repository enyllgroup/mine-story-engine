---
name: minecraft-asset-creator
description: "Gerar texturas originais e modelos editáveis Blockbench, ou catalogar um objeto personalizado MineStory. Usar ao precisar de novo personagem, item ou cuboides."
---

Executar `scripts/run.py --output library/generated` para gerar texturas pixeladas originais e documentos `.bbmodel` editáveis. Executar `scripts/run.py --output library/generated --custom objeto.json` para registrar uma definição personalizada no catálogo persistente. Descrever novas formas por cuboides `voxels` no storyboard; usar só materiais suportados. Preservar licenças e versões. Consultar `minestory/assets.py` e `minestory/scene_schema.py` para formatos reais.

Executar o script com `--help` para argumentos. O wrapper usa a `.venv` do repositório e não instala dependências. Todos os subprocessos recebem listas de argumentos, sem interpolação em shell.
