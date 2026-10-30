# Projetos nativos Mine-imator

Este bridge cria `.miproject` **para o Mine-imator 2.0.2 oficial**. O renderer Blender legado não participa deste caminho. A geração de JSON é uma integração de arquivo; a exportação depende da interface real do Mine-imator. Não foi encontrada uma API pública de exportação em lote.

## Gerar o teste técnico

```bash
.venv/bin/python scripts/create_mineimator_test_project.py --quality final
# Prévia: --quality preview
```

Saída: `productions/mineimator-validation/test.miproject`, com texturas originais em `assets/` ao lado do projeto. O gerador recusa tanto um `.miproject` existente quanto um diretório `assets/` existente, antes de escrever, e cria o projeto com abertura exclusiva. Para cada nova versão, use `--output productions/NOVO_JOB/test.miproject` em um diretório novo; não sobrescreva a produção anterior. O teste contém dois rigs humanos Minecraft, caminhada articulada, descoberta, levantamento de uma carta original, reação e aproximação de outro personagem. Árvores e uma pequena banca são montadas com modelos de blocos nativos. Não é um template obrigatório para narrações futuras nem um diretor visual completo.

O projeto configura 1080 × 1920 em `--quality final` (padrão), ou 540 × 960 em `--quality preview`, com 30 FPS e quadros 0–599. Para a saída, a exportação precisa ser conferida no próprio programa, inclusive FPS, intervalo e câmera. Se o áudio de teste for mais curto, a montagem final deve terminar junto com esse áudio, preservando a velocidade e a duração da voz.

O arquivo-base `templates/mineimator/base-2.0.2.miproject` foi salvo pela aplicação oficial em execução. Ele contém somente a configuração de um projeto vazio, sem modelos, texturas ou recursos oficiais redistribuídos. Os modelos Minecraft usados no render são carregados pela instalação local legítima do Mine-imator.

## Formato auditado

Código upstream: [stuffbydavid/Mine-imator](https://github.com/stuffbydavid/Mine-imator), especialmente `project_load_*`, `project_save_*`, `value_get_state_vars` e `render_update_camera`.

- `format: 34`, `created_in: "2.0.2"`.
- Seções: `project`, `render`, `background`, `templates`, `timelines`, `resources`.
- Template define modelo/bloco/item; timeline referencia `temp` e contém `keyframes` com números de quadros como chaves JSON.
- Rigs humanos: template `type: "char"`, `model.name: "human"`, `model.state: {"type":"wide","variant":"steve"}`. Os estados de um projeto são **objetos JSON**, embora o catálogo `.midata` use strings compactas.
- Blocos usam nomes agrupados do catálogo Mine-imator, por exemplo `name: "log", state: {"variant":"oak","axis":"y"}` e `name: "wool", state: {"color":"red"}`. Não passar IDs Minecraft como `oak_log` diretamente nesse campo.
- Partes do rig usam `type: "bodypart"`, o mesmo `temp` da raiz, `part_of` apontando para a raiz e `model_part_name` exato, como `right_arm`. O campo `parent` representa a hierarquia real.
- Em keyframes, `POS_X/POS_Y/POS_Z` são coordenadas internas; **Z é a altura**. Vetores em recursos e no work camera têm conversão própria. Não aplicar a mesma troca de eixos indiscriminadamente.
- Câmera com rotação zero olha para +Y; pitch positivo em `ROT_X` aponta para baixo. A câmera visível é escolhida por `app_update_animate`; o projeto usa `view_main_camera: -5` para acompanhar essa câmera ativa. `view_draw` trata esse valor técnico explicitamente e evita entregar o ID textual da câmera a `instance_exists` durante o carregamento.
- `project.tempo` é FPS de animação. O FPS do exportador deve ser verificado separadamente.

## Validação

```bash
.venv/bin/python -m pytest tests/test_mineimator_project.py -q
```

Os nove testes passam e verificam hierarquia, referências, resolução dos PNGs e estados nativos. Esses testes **não provam renderização**. A aplicação abriu a cena gerada durante esta sessão: árvores, banca e texturas nativas foram visualizadas. A primeira inspeção revelou câmera inclinada para cima e estados no formato errado; ambos foram corrigidos no gerador. A câmera e a orientação dos personagens foram verificadas em seguida pela imagem nativa `productions/mineimator-validation/native-frame-299.png` (540 × 960), com personagem, carta e contato da mão visíveis. Depois disso, a aplicação exportou o master completo: 600 quadros, 20 segundos, 1080×1920/30 FPS. O monitor confirmou o log de conclusão e o MP4 real. A montagem final com narração sintética e ASS tem 539 quadros e foi inspecionada em folha de contato e frames completos. Os 87 testes de código passaram. [Detalhes e limites](MINEIMATOR-VALIDATION.md).

## Limites atuais

O script é um teste técnico reproduzível de geração de projeto. Ainda não implementa compilação arbitrária de qualquer storyboard, catálogo persistente de animações nativas ou exportação completamente sem interação. O teste desta sessão exportou o vídeo completo e montou áudio/legendas, mas não comprova direção livre para uma nova narração. O arquivo gerado pode ser aberto e editado no Mine-imator; automação da GUI está em `scripts/mineimator_gui.py`. Não alterar flags de licença, remover marca por pós-processamento ou modificar o executável.

## Controlador de exportação com limites explícitos

`scripts/export_mineimator.py` automatiza as operações de exportação observadas nesta sessão no perfil **Mine-imator 2.0.2 Linux, idioma inglês, tema claro, escala de UI padrão, editor maximizado em uma tela X11 de 1600 × 1000**. Não é uma API do programa nem automação independente do layout. O agente deve inspecionar o editor e conferir o perfil antes de usar os dois indicadores abaixo; eles não exigem uma nova confirmação do usuário.

```bash
.venv/bin/python scripts/export_mineimator.py \
  --display :100 \
  --project /caminho/novo-job/test.miproject \
  --output /caminho/novo-job/native.mp4 \
  --editor-ready --profile-confirmed
```

O projeto precisa estar aberto, sem popup, com um evento `Opening project: ...` seguido de `Project loaded` no log nativo. O perfil aceita somente projetos de teste com até 20 segundos, 30 FPS e resolução 540 × 960 ou 1080 × 1920. A exportação usa MP4, qualidade Best (5 Mbps), áudio desativado, objetos ocultos desativados e renderização em alta qualidade ativada. A marca d'água deve estar desativada pela configuração legítima Full do programa; o controlador não ativa licenças nem modifica essa opção. A narração será misturada depois ao master silencioso.

O controlador recusa destinos/relatórios já existentes e exportações anteriores sem conclusão. Confere o tamanho da janela, lê as dimensões/MP4/FPS por OCR, verifica os quatro checkboxes na captura da interface e confirma o título do seletor nativo antes de inserir o caminho. Se o perfil divergir, preserva as capturas e interrompe a operação. Não seleciona confirmações de sobrescrita.

A conclusão exige **evidências combinadas**: log de uma exportação para o destino exato, configurações nativas corretas, toast `Movie exporting finished!` e `ffprobe` confirmando H.264, resolução, FPS, quantidade de frames e duração. Um arquivo MP4 parcialmente escrito não satisfaz essa verificação. As evidências são gravadas em `native.export.json`; o relatório mantém inspeção visual/semântica como uma etapa separada.

`--check` executa apenas os checks de arquivo/log, sem tocar na GUI. Para observar uma exportação já iniciada pela interface:

```bash
.venv/bin/python scripts/export_mineimator.py \
  --project /caminho/novo-job/test.miproject \
  --output /caminho/novo-job/native.mp4 \
  --monitor --timeout 3600
```

`--monitor` só lê o log e o vídeo. Os oito testes de guardas passam em `tests/test_mineimator_export.py`. A captura real `export-quality-popup.png` passou pelos checks de OCR e checkboxes. **O fluxo inteiro de cliques deste controlador ainda não foi executado**; a exportação que originou o teste desta sessão foi conduzida por chamadas dos helpers com inspeção da interface real. O modo `--monitor` foi executado e confirmou esse master de 600 quadros. Não usar os testes unitários como prova de que novos layouts funcionam.

O master testado ainda usava o ID textual da câmera e produziu duas mensagens
`ToInt` durante o carregamento, sem bloquear a exportação. O gerador atual usa
`view_main_camera: -5` conforme o fonte; essa revisão não foi recarregada na GUI
após o render e não deve ser apresentada como correção de runtime já confirmada.
