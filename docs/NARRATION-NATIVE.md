# Narração real: preparação para Mine-imator

O analisador é independente do renderer e não usa TTS, API paga ou direção por
modelo local. O Codex da conversa interpreta o resultado posteriormente.

```bash
.venv/bin/python scripts/analyze_native_narration.py entrada/voz.wav \
  --output productions/NOVO_JOB --model large-v3-turbo --threads 2
```

O script guarda uma cópia **byte a byte** do áudio em `input/`, SHA256 e duração
reais, transcrição bruta, palavras/segmentos com tempos, pausas medidas e ASS/SRT
com Pixelify Sans. Os pesos Whisper são reutilizados em `library/cache/models`;
o cache textual e os arquivos desta narração pertencem apenas ao job. Uma história
não vira template permanente de direção ou parte do personagem.

O padrão é Whisper large-v3-turbo, inferência CPU int8. `--model large-v3` é uma
opção mais pesada, que não garante eliminar ambiguidades de pronúncia. O primeiro
download dos pesos é gratuito; execuções seguintes reutilizam o cache. Duas
threads deixam capacidade para o programa de animação. A transcrição utiliza
timestamps acústicos do Whisper e recorte por pausas medidas, **não forced
alignment independente**. Não apresentar limites estimados como precisão fonética
verificada.

Para alinhar a transcrição existente com outro modelo acústico local, mantendo
os tempos originais como alternativa quando a confiança for baixa:

```bash
.venv/bin/python -m minestory native align \
  --audio productions/NOVO_JOB/input/narracao.wav \
  --transcript productions/NOVO_JOB/transcript.json \
  --output productions/NOVO_JOB/alinhamento --threads 1
```

O modelo português Wav2Vec2 ONNX quantizado é obtido gratuitamente na primeira
execução e permanece no cache privado. O relatório distingue palavras alinhadas
e segmentos preservados com os tempos Whisper. O alinhamento força o texto
fornecido sobre o áudio: **não confirma que as palavras transcritas sejam as
palavras faladas**. Revise palavras ambíguas antes de gerar legendas finais.

Uma produção existente com outro SHA256 é recusada. Repetir o comando sobre a
mesma transcrição preserva textos e legendas revisados, sem chamar ASR novamente.
Se uma etapa falhar após criar artefatos parciais, preserve o job e use outro
diretório para a tentativa seguinte; não remover evidências para forçar a escrita.

## Revisão de palavras

Leia a transcrição e os trechos correspondentes. Confiança alta do ASR não prova
que uma palavra esteja correta. Se dois reconhecedores concordarem num termo
incompatível com o sentido, registre a dúvida no job; não substituir por uma
palavra apenas porque ela combina melhor com a história. A direção visual pode
registrar separadamente sua interpretação sem alterar a voz ou fingir certeza
acústica.

Depois de uma revisão com evidência suficiente, faça a correção em uma nova versão
de `transcript.json`, preservando `transcript.raw-asr.json`, o SHA256 do áudio e
os tempos brutos. Registre índice da palavra, texto anterior, texto revisado,
motivo, responsável e estado da revisão. Não inventar um novo timestamp ao trocar
uma grafia; se a segmentação mudar, o alinhamento também precisa de revisão.
Gere novas legendas em um diretório novo com `minestory.captions.write_captions`.
Nenhuma correção textual autoriza retimar ou substituir a narração.

```bash
.venv/bin/python -m pytest tests/test_native_narration.py -q
```

Os testes cobrem preservação do áudio, isolamento dos artefatos do job,
idempotência e recusa de sobrescrita com uma nova narração.
