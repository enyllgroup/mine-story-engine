# Autoria de cenas nativas reutilizável

`minestory/native_scene.py` é uma API de autoria de arquivos Mine-imator34.
Não contém um tema fixo e não chama Blender. A direção continua sendo feita pelo
Codex a partir do áudio real. Um arquivo JSON válido ainda precisa ser carregado
no programa oficial e inspecionado antes de se afirmar que o resultado funciona.

## Contrato

- `NativeProject(job, duration=..., name=..., quality='preview')` usa a duração
  real da narração e30FPS. `preview` é540×960; `final`,1080×1920. O último quadro
  é calculado por `ceil(duration*30)-1`; o vídeo final termina junto da voz com
  precisão de um quadro, sem retiming.
- `scene(id,start,end,origin=...)` cria uma pasta nativa com visibilidade limitada
  ao intervalo. Cada espaço de encenação pode ter uma origem independente. As
  partes filhas devem herdar a visibilidade; confirmar isso na aplicação real.
- `block(...)` usa modelos/texturas do catálogo nativo da instalação. A tabela
  `BLOCKS` mapeia nomes de variantes, por exemplo carvalho→`log`+estado `oak`.
- `cuboid_model(...)`, `model_part(...)` e `model_box(...)` criam modelos
  `.mimodel` originais e articulados dentro do job. Geometria usaYvertical;
  transforms de projeto usamZvertical. O modelo carrega seu atlas original com
  `model_tex/model_tex_material/model_tex_normal='null'`; `default` pode resolver
  o pack Minecraft errado. A raiz registra todas as partes numa lista plana,
  enquanto `parent` define a hierarquia das timelines.
- `character(directory,id,...)` instancia uma versão imutável do personagem,
  copiando seus arquivos para o job. `clip(...)` compõe as ações dessa versão.
- `key(...)` aceita eventos temporais e campos nativos. `save()` materializa
  canais independentes em todos os tempos relevantes: inserir um salto ou uma
  mudança de visibilidade não deve apagar posição, trajetória, escala ou rotação
  anteriores. Campos booleanos usam troca discreta; canais numéricos,
  interpolação linear. Outros tipos de easing precisam ser tratados
  explicitamente antes de se anunciar suporte.
- `audio(...)` copia um WAV do job como recurso nativo. A voz original é
  preservada separadamente; a referência audível do projeto pode ser o mix
  derivado com efeitos. Não reproduzir voz original e mix simultaneamente.
  O campo nativo `SOUND_END` é um deslocamento em relação ao fim do arquivo:
  `0` significa a fonte completa. A API converte um endpoint absoluto opcional
  para esse offset após consultar a duração real; não somar a duração duas vezes.
- `save()` valida IDs, hierarquia, recursos existentes, tempos e valores finitos.
  Modelos, recursos e saídas existentes nunca são sobrescritos.

## Memória permanente e arquivos da história

Código de autoria, fluxo de direção, perfis sonoros e personagem selecionado são
reutilizáveis. Narração, objetos específicos, roteiro, eventos, projetos e mixagens
de cada assunto ficam exclusivamente em seu diretório `productions/`, ignorado
pelo Git. Não transformar uma produção em tema ou template permanente.

## Corrigir apenas uma faixa de quadros

Para uma versão revisada do projeto, crie outro `.miproject` no mesmo diretório
de assets e defina a região nativa usando início inclusivo e fim exclusivo:

```bash
.venv/bin/python -m minestory native retake \
  --project productions/NOVO_JOB/mineimator/story-revisado.miproject \
  --output productions/NOVO_JOB/mineimator/retake-0300-0450.miproject \
  --start-frame 300 --end-frame-exclusive 450
```

Abra e exporte essa região no Mine-imator com `native gui` e `native export`.
O relatório do exportador precisa confirmar o projeto, o arquivo e seu SHA256.
Na montagem, `native finish --retakes retakes.json` substitui as faixas em uma
única codificação final. Exemplo de manifesto relativo ao próprio JSON:

```json
{"retakes":[{"video":"retake.mp4","export_report":"retake.export.json",
             "start_frame":300,"end_frame_exclusive":450}]}
```

As faixas devem ser ordenadas, não sobrepostas e ter a mesma resolução e FPS do
master. O programa valida hashes, projeto e número exato de quadros, preserva
os arquivos de origem e não estica o áudio. O corte e a montagem foram testados
com arquivos de teste; cada região precisa também ser exportada e revisada no
Mine-imator real antes do uso em uma produção.

## Projeto portátil

```bash
.venv/bin/python scripts/package_native_production.py \
  --job productions/NOVO_JOB \
  --project productions/NOVO_JOB/mineimator/story.miproject \
  --output productions/NOVO_JOB/projeto.zip
```

O pacote mantém os caminhos relativos do `.miproject`, modelos, texturas e mix,
inclui roteiro/legendas e a narração original se presentes, e validaCRC/hashes.
Não carrega bibliotecas externas ao job, programas ou texture packs instalados.
Os OGGs do jogo não são distribuídos isoladamente: a produção atual inclui
somente sua mixagem narrada derivada. Os direitos de cada fonte continuam
registrados separadamente. O arquivo existente é recusado.

Validação programática: `tests/test_native_scene.py` e
`tests/test_native_package.py`. Qualidade visual, atuação, contato e visibilidade
continuam exigindo o Mine-imator real e inspeção de frames.
