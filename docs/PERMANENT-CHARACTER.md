# Personagem permanente no Mine-imator

`minestory/native_character.py` gera um `.mimodel` articulado e um atlas original a partir de um perfil privado. O perfil, a seleção, os modelos produzidos, as fotos e as produções ficam fora do Git. A seleção está em `library/characters/channel_host/selection.json`. Ela não representa uma aprovação artística recebida.

A versão selecionada inclui cabeça, cabelo, olhos, boca, armação, corpo e membros articulados, além de pontos de fixação para objetos. As políticas do perfil são obrigatórias: com `appearance_policy.glasses_always_on: true`, os óculos permanecem colocados e `apply_clip` recusa movimentos que os levantem, removam, ocultem ou deformem. Expressões podem usar cabeça, boca e corpo.

## Criar e usar uma versão

Execute `python scripts/build_native_character.py --help` para os argumentos. Forneça um perfil privado e escolha novos diretórios para a versão e para o projeto de inspeção; o builder recusa sobrescrita. Use a seleção registrada na biblioteca para novas cenas.

```python
from minestory.native_character import add_character, apply_clip
add_character(project, character_directory, job_directory, actor_id="host")
apply_clip(project, character_directory, "host", "walk", start=0, end=120, repeat=True)
```

O importador copia os recursos para `JOB/assets/host/`, ajusta o atlas e cria resources, template e hierarquia de timelines nativos. Cuboides usam Y como altura; keyframes de projeto usam Z. Para câmera no lado -Y, `ROT_Z:180` orienta o ator para ela.

## Atuação e validação

A biblioteca contém curvas nativas para andar, correr, apontar, segurar, entregar, receber, reagir, pular, sentar e cair. A lista exata depende da política do perfil. As curvas podem ser compostas e os localizadores `right_grip` e `left_grip` recebem objetos. Curvas existentes não garantem atuação natural: inspecione contato, movimentos e enquadramento no projeto e no vídeo real.

Modelos próprios usam `model_tex:"null"` para carregar seu atlas. A lista `parts` pertence à raiz do modelo e contém todas as partes; timelines `bodypart` definem hierarquia por `parent`. `apply_clip` materializa canais nos keyframes para preservar trajetórias ao compor movimentos.

Uma versão privada do personagem foi aberta e renderizada no Mine-imator; a inspeção verificou a importação e a aparência em alguns quadros. Isso não aprova todas as animações, a semelhança ou a qualidade artística. Prévias são somente para controle interno; entregue apenas o vídeo final solicitado depois da revisão.
