# Validação de áudio e legendas

Os testes usam **áudios sintéticos criados exclusivamente para validar a engine**. Não são a narração do usuário. A produção recebe o arquivo original, não usa TTS, não modifica a velocidade e não troca a voz. Os WAVs Piper têm 70,461 s (cartas) e 42,794 s (Sol).

## Transcrição efetivamente executada

Hardware: 3 vCPUs Xeon, aproximadamente 10 GB de RAM, sem GPU exposta. `faster-whisper 1.2.1`, CPU `int8`, duas threads, idioma `pt`, `beam_size=5`, VAD ligado e timestamps por palavra. O modelo é baixado uma vez; as transcrições são cacheadas pelo SHA-256 do áudio e pelas configurações.

A comparação usa **os mesmos WAVs Piper** para os dois modelos. WER é distância de edição entre palavras dividida pelo número de palavras do texto de teste. Normalização: minúsculas, remoção de pontuação e equivalência de `8/oito` e `20/vinte`; acentuação preservada. O roteiro sintético é a referência pretendida, não uma anotação humana independente do som realmente sintetizado.

| Teste | Palavras de referência | Modelo | Erros | WER | Tempo de inferência registrado |
|---|---:|---|---:|---:|---:|
| Cartas, 70,461 s | 204 | small | 18 | 8,82% | 36,193 s |
| Cartas, 70,461 s | 204 | large-v3-turbo | 4 | 1,96% | 63,023 s |
| Sol, 42,794 s | 115 | small | 5 | 4,35% | 8,967 s |
| Sol, 42,794 s | 115 | large-v3-turbo | 1 | 0,87% | 23,535 s |

São tempos individuais de execuções reais, não um benchmark isolado: havia outras tarefas no ambiente. As comparações de `small` reutilizaram o resultado real previamente cacheado; a tabela mostra o tempo da inferência original, não o tempo de leitura desse cache. Os dois modelos ocupam aproximadamente 2,0 GB de cache no ambiente; `large-v3-turbo` isoladamente tem custo maior que `small` em disco, memória e CPU.

`large-v3-turbo` melhorou os dois testes e é a escolha fundamentada para qualidade de transcrição neste ambiente. Ainda reconheceu `preço` como `peso`, `comprar` como `contar` e `um baú` como `o mau` no teste de cartas. No teste do Sol acrescentou o artigo `a` em `Oceanos e a atmosfera`. Esses resultados **não foram corrigidos silenciosamente com o roteiro**. Não há evidência para prometer transcrição sem erros em narrações inéditas.

A primeira tentativa com eSpeak NG pt-br apresentou pronúncia robótica e muitos erros de ASR. Esses arquivos foram preservados como testes antigos; seus resultados não são usados na comparação acima. A geração neural de fixtures usa Piper `1.8.0`, voz `pt_BR-faber-medium`, cujo [MODEL_CARD declara dataset CC0](https://huggingface.co/rhasspy/piper-voices/blob/main/pt/pt_BR/faber/medium/MODEL_CARD). O [motor Piper é GPL-3.0](https://github.com/OHF-Voice/piper1-gpl). TTS é uma dependência opcional de teste, sem relação com a execução normal.

## Sincronização com pausas conhecidas

Fixture `sincronia_PIPER_SINTETICO.wav`: três frases sintetizadas separadamente, concatenadas com **pausas digitais exatas de 0,800 s**. Duração de 8,344 s. As janelas exatas das frases e as pausas estão em `examples/audio/sincronia_piper_ground_truth.json`.

- Inferência real `large-v3-turbo`: 10,608 s; 20 palavras reconhecidas para 19 palavras do roteiro.
- Antes do refinamento, duas palavras invadiam as pausas inseridas: sobreposição somada de 0,728 s.
- O refinamento corta somente a parte do timestamp que invade silêncio medido por FFmpeg. Preserva `raw_start` e `raw_end` como evidência; não redistribui palavras por proporção de duração.
- Depois do refinamento: nenhuma palavra invade uma pausa inserida por mais de 20 ms. Sobreposição residual total de 0,000043 s por arredondamento. Sobreposição com os silêncios acústicos detectados: 0,000 s.
- O conteúdo ainda apresentou três erros de edição (`bloco` → `do oco`; `carta` → `cada`): WER de 15,79% neste teste curto. Sincronização temporal e precisão textual são critérios distintos.

O método implementado é **timestamps do Whisper com refinamento por silêncio acústico**. `forced_alignment` fica explicitamente `false`. Não foi instalado nem validado um alinhador fonético independente, como WhisperX. O teste comprova tratamento de pausas e preservação dos tempos; não comprova precisão fonética para cada palavra.

## Legendas e som

`tests/test_audio_captions.py`: cinco testes reais passaram, usando WAV PCM e FFmpeg para verificar duração, detecção de silêncio, preservação do conteúdo textual das legendas, destaque por palavra, posição dentro da área reservada, neutralização de comandos ASS presentes no texto e posicionamento de efeitos relativos à cena. A mixagem conserva a duração e a velocidade da narração. Os efeitos são ondas originais geradas proceduralmente, com nível baixo e ducking sob a voz; nenhuma música do Minecraft é distribuída.

ASS e SRT são editáveis. A legenda mostra no máximo quatro palavras por grupo, destaca apenas a palavra ativa e reserva margens conservadoras para botões e textos das plataformas. Essas margens não garantem compatibilidade com toda mudança futura de interface; o vídeo renderizado deve ser inspecionado.

Foi detectada e corrigida uma incompatibilidade real: `faster-whisper 1.2.1` chama `av.open(metadata_errors=...)`, removido em PyAV 19. A instalação testada fixa **PyAV 16.1.0**. A carga do modelo e a inferência passaram com essa versão.

## Reprodução

```bash
# Opcional: somente para gerar áudios sintéticos de validação.
uv pip install --python .venv/bin/python piper-tts==1.8.0
.venv/bin/python scripts/generate_neural_test_audio.py

# Testes de PCM/FFmpeg/legendas/efeitos, sem download de modelos.
.venv/bin/python -m pytest tests/test_audio_captions.py -q

# Recalcula métricas a partir das transcrições reais salvas; não edita transcrições.
.venv/bin/python scripts/validate_audio_fixtures.py
```

Para repetir inferência em vez de ler o cache, execute `audio.analyze(..., model="large-v3-turbo", force=True)`; isso baixa o modelo se necessário. Os scripts de geração preservam fixtures neurais existentes. Hashes dos WAVs, alterações de palavras, métricas e metadados verificáveis estão em [audio-validation.json](audio-validation.json). As transcrições de evidência estão em `examples/audio/*_transcript.json`.
