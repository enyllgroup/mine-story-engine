---
name: minecraft-camera-director
description: "Definir câmeras simples legíveis em vídeo vertical MineStory. Usar ao enquadrar atores e objetos, reservar legendas ou corrigir cortes e trajetórias."
---

Editar `camera.position`, `camera.target`, `camera.scale` e `end_position` em cada cena. Manter atores e acontecimentos essenciais na região superior a 70% da imagem; reservar a direita e o rodapé para interfaces sociais. Preferir movimentos curtos e planos legíveis. Executar `scripts/run.py STORYBOARD --audio AUDIO --quality preview --output DIRETORIO` e inspecionar frames reais; projeção numérica não detecta todas as oclusões.

Executar o script com `--help` para argumentos. O wrapper usa a `.venv` do repositório e não instala dependências. Todos os subprocessos recebem listas de argumentos, sem interpolação em shell.
