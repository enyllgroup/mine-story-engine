# Skills locais executáveis

As 11 skills ficam em `.agents/skills/<nome>/SKILL.md`, formato de descoberta por projeto do Codex. Abra uma nova sessão do Codex na raiz do repositório para carregar seus metadados. Os scripts funcionam diretamente, sem depender dessa descoberta ou de MCP adicional.

O formato segue o [guia oficial de skills](https://learn.chatgpt.com/docs/build-skills) e o [skill-creator oficial](https://github.com/openai/skills/tree/main/skills/.system/skill-creator). Os scripts `init_skill.py`, `generate_openai_yaml.py` e `quick_validate.py` foram lidos antes de executar. A validação oficial dos 11 arquivos passou. Nenhuma skill com API faturada foi instalada.

| Skill | Responsabilidade executada | Interface do wrapper |
|---|---|---|
| `narration-analyzer` | Whisper local e timestamps reais | `AUDIO --output DIR` |
| `visual-director` | Gerar storyboard validado | `TRANSCRIPT --output JSON --director auto` |
| `minecraft-world-builder` | Construir e renderizar geometria do storyboard | `STORYBOARD --audio AUDIO --output DIR` |
| `minecraft-asset-creator` | Gerar texturas e `.bbmodel`; catalogar JSON customizado | `--output DIR [--custom JSON --license LICENCA]` |
| `minecraft-character-animator` | Executar ações sobre o rig real | `STORYBOARD --audio AUDIO --output DIR` |
| `minecraft-scene-director` | Executar eventos e montar cenas | `STORYBOARD --audio AUDIO --output DIR` |
| `minecraft-camera-director` | Executar câmeras e produzir prévia para inspeção | `STORYBOARD --audio AUDIO --output DIR` |
| `subtitle-director` | Exportar SRT/ASS com palavra ativa destacada | `TRANSCRIPT --output DIR` |
| `sound-designer` | Sintetizar efeitos e mixar com ducking | `STORYBOARD --audio AUDIO --output DIR` |
| `render-pipeline` | Produzir MP4 desde o áudio | `AUDIO --quality preview` |
| `visual-quality-control` | Inspecionar mídia e gerar folha de contato | `VIDEO --output DIR [--storyboard JSON --transcript JSON]` |

Execute, por exemplo:

```bash
.venv/bin/python .agents/skills/subtitle-director/scripts/run.py \
  examples/audio/sincronia_transcript.json --output productions/legendas-teste
```

Cada wrapper calcula a raiz pelo seu caminho e usa a `.venv` do projeto quando disponível. `scripts/run.py --help` mostra os argumentos da implementação real. O despachante compartilhado `_runner.py` evita duplicar a engine em 11 processos diferentes. Construção, atuação, cena e câmera usam o mesmo renderizador; as respectivas skills orientam partes diferentes do mesmo grafo temporal.

Os 11 wrappers passaram `--help`. Foram executados também a geração efetiva de 30 assets, a criação de 6 grupos de legendas do áudio sintético de sincronização e uma mixagem de efeitos com o áudio. A evidência está em `docs/skill-validation.json`; os testes completos de produção são documentados separadamente.

# O que o QC comprova

`minestory.qc.inspect_video()` usa FFprobe e decodifica frames reais via FFmpeg. Verifica formato H.264/AAC, 9:16, FPS, duração contra o áudio, tempos e cobertura de cenas, quadros pretos, pouca variação da região da cena e repetição do plano. Quando disponível, lê a projeção de atores e limites medidos pelo Blender, com avisos para cortes e sobreposição à faixa das legendas.

Escreve `qc_report.json` e `contact_sheet.jpg`, incluindo cenas afetadas. A amostragem é de até 1 frame/segundo, limitada a 180 amostras em produções longas; falhas entre amostras podem escapar. A detecção de congelamento desconsidera a parte inferior reservada a legendas. Saídas intencionais de um personagem e pausas visuais podem gerar avisos que exigem inspeção.

`technical_pass` significa apenas que os testes técnicos implementados passaram. Coerência com a narração, legibilidade real do texto, oclusões e fidelidade artística vanilla continuam itens explícitos de revisão por frames. A engine não usa uma heurística de pixels para declarar essas qualidades aprovadas. Os testes em `tests/test_qc.py` criam e inspecionam vídeos reais, incluindo um vídeo preto, um vídeo com duração divergente e um vídeo animado válido.
