# Operação

## Estrutura

`minestory/`: CLI, análise de áudio, direção, contrato de cenas, compilador Blender, biblioteca, legendas, sons, QC e sessões. `.agents/skills/`: 11 skills locais com scripts executáveis; compartilham a mesma implementação. `assets/fonts/`: Pixelify Sans e OFL. `examples/`: narrações sintéticas explicitamente identificadas, planos de demonstração e scripts reprodutíveis. `tests/`: contratos, áudio real, FFmpeg, segurança de entradas e preservação. `docs/`: decisões, evidências, versões e validação.

Pastas locais excluídas do Git: `.venv`, `.tools`, `.models`, `.cache`, `library` e `productions`. Downloads de modelos não são código do projeto. Não apagar a biblioteca para atualizar o repositório.

## Comandos

```bash
.venv/bin/python -m minestory --help
.venv/bin/python -m minestory analyze voz.mp3 --output trabalho/transcript.json
.venv/bin/python -m minestory validate trabalho/storyboard.json
.venv/bin/python -m minestory render trabalho/storyboard.json --audio voz.mp3 --transcript trabalho/transcript.json --output productions/versao-nova --quality preview
.venv/bin/python -m minestory qc productions/JOB/video_final.mp4 --storyboard productions/JOB/storyboard.json --transcript productions/JOB/transcript.json --output productions/JOB/reinspection
.venv/bin/python -m minestory assets list
```

O launcher opcional `python -m minestory launcher` usa Tk para escolher o áudio e acompanhar logs. Requer Tk e sessão gráfica; não foi validado neste servidor sem display. A CLI e a produção pelo Codex não dependem dele.

## Novos assets

Consulte o catálogo antes de criar. Uma definição original de objeto pode conter `kind: custom`, `voxels: [{position: [x,y,z], size: [x,y,z], material: stone}]`. Materiais suportados constam em `scene_schema.py`. Posições usam metros/blocos e eixo Z para cima; atores têm 2 blocos de altura. Um prop pode combinar qualquer número de cuboides dentro do limite de 400. Para animar partes separadamente, use props distintos e ações coordenadas; não há IK nem rig automático de anatomia arbitrária.

```bash
.venv/bin/python -m minestory.assets --help
.venv/bin/python .agents/skills/minecraft-asset-creator/scripts/run.py --output library/generated
.venv/bin/python -m minestory assets add meu_objeto.json --kind prop-definition --license CC0-1.0
```

Texturas originais e arquivos `.bbmodel` são gerados com versão e hashes. Modelos `.bbmodel` exportados são editáveis; **não há importador completo de plugins, meshes, IK ou Molang do Blockbench**. Para usar modelos editados, converta explicitamente os cuboides para o contrato `voxels`. Não alegar suporte a qualquer `.bbmodel` sem adapter e testes.

As definições usadas são registradas por hash em `library/catalog.sqlite3` e `library/objects`; o histórico associa recursos aos jobs. Os personagens Lia, Noa e Ivo são originais e usam o mesmo rig, com roupas distintas. O nome não replica personagens de terceiros.

## Identidade visual

`assets/identity.json` documenta paleta e zonas reservadas. A fonte instalada é `assets/fonts/PixelifySans.ttf` (OFL). Ajuste texto/âncora/contorno em `captions.py` e cores/texturas em `assets.py`. Alterações no gerador de assets precisam incrementar `assets.VERSION`; os arquivos existentes são imutáveis e uma colisão com conteúdo diferente gera erro. O hash do código do renderer participa do cache das cenas.

O arquivo de identidade é documentação dos valores, não um tema recarregado dinamicamente. Mudanças devem ser validadas por frame real e exportação de legendas, incluindo acentos.

## Cache, velocidade e retomada

O áudio é cacheado por SHA256, modelo, versão do transcritor e configuração. O modelo é cacheado localmente. Cada cena tem chave por JSON, versão Blender, código dos assets/renderer, resolução/FPS e parâmetros de exportação. Uma cena inalterada reutiliza o MP4 verificado por hash; cenas alteradas recebem outras chaves. PNGs parciais são retomados. Jobs paralelos são isolados e limitados à CPU; em 3 CPUs, usar `--jobs 1`.

```bash
# Job de CLI interrompido (mesmo áudio e qualidade):
.venv/bin/python -m minestory produce voz.mp3 --resume productions/JOB --quality preview
# Job dirigido nesta conversa interrompido:
.venv/bin/python -m minestory finish productions/JOB --quality preview
```

O hash de entrada precisa coincidir. Um job concluído não pode ser regravado; use `version` para outra exportação. Revisões do plano também devem criar outra versão. Logs e frames completos permanecem no cache após falha. Não remover caches em uso. Não existe política automática de exclusão de produções.

## Diagnóstico

- Consulte `production_report.json`, `events.jsonl`, `render-*.log`, `assemble.log` e `qc/qc_report.json`.
- HTTP401 no Codex externo: a autenticação não é válida para executar a chamada. Use o próprio Codex da conversa; não copiar tokens, não criar chave paga e não alterar autenticação automaticamente.
- Falta de `blender`/`ffmpeg`: instalar pelos distribuidores oficiais. A engine não usa privilégios administrativos nem executa instaladores remotos opacos.
- Primeira transcrição demora: download público do modelo; avisos de Hugging Face sem token não significam cobrança. Após o cache, inferência é local. Falhas de rede devem ser resolvidas na política de ambiente, sem contornar o proxy.
- Erro de `metadata_errors` no PyAV: usar `av==16.1.0`; incompatibilidade com PyAV19 foi reproduzida e corrigida.
- EGL em um host diferente: executar smoke test. Neste host houve mensagens EGL iniciais, mas o fallback software gerou frames reais. Não silenciar um erro fatal ou assumir que todo host terá o mesmo comportamento.
- Legenda incorreta: verificar áudio e palavras de baixa confiança. Timestamps são estimados pelo Whisper com recorte acústico de pausas. Não substituir automaticamente a fala pelo texto desejado. WhisperX/CTC independente ainda não foi integrado/validado.
- QC técnico falhou: MP4 fica pendente; não recebe o nome final. Leia `affected_scenes`, corrija em outra versão e aproveite o cache de cenas não alteradas. Avisos editoriais e de enquadramento exigem inspeção, mesmo quando o gate técnico passa.

## Instalação reproduzível

`requirements.lock` contém versões resolvidas para Python3.12. Para reproduzir essas versões, `uv pip install --python .venv/bin/python -r requirements.lock` e depois `uv pip install --python .venv/bin/python --no-deps -e .`. O bootstrap normal instala os requisitos compatíveis do projeto. Blender4.3.2 e FFmpeg7.1.5 foram as versões efetivamente testadas; versões maiores precisam de smoke test.
