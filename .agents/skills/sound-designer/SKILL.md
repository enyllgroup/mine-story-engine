---
name: sound-designer
description: "Sintetizar efeitos originais e misturar com narração MineStory sem música licenciada. Usar para passos, impactos, descobertas e ações do storyboard."
---

Executar `scripts/run.py STORYBOARD --audio NARRACAO --output DIRETORIO` para gerar efeitos originais e a mixagem. Vincular cada som a uma ação; usar efeitos discretos e pausas entre eventos. Preservar a voz original e sua velocidade; não usar músicas ou sons Minecraft como se fossem de livre uso. Consultar `minestory/sound.py` para os nomes reconhecidos e a normalização da mixagem.

Executar o script com `--help` para argumentos. O wrapper usa a `.venv` do repositório e não instala dependências. Todos os subprocessos recebem listas de argumentos, sem interpolação em shell.
