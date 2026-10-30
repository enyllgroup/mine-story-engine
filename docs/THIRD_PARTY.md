# Licenças e proveniência

Código MineStory: MIT, arquivo [LICENSE](../LICENSE). Texturas, personagens, modelos e efeitos procedurais originais gerados por este projeto: CC0-1.0, conforme manifestos. Nenhum arquivo Minecraft/Mojang é distribuído e não há logotipo oficial.

| Componente | Fonte | Uso/licença |
|---|---|---|
| Blender4.3.2 | https://www.blender.org/about/license/ | GPL; ferramenta instalada no ambiente, não embutida no repositório |
| FFmpeg7.1.5 | https://ffmpeg.org/legal.html | Build instalado com GPL/libx264/libass; ferramenta externa |
| SFX Minecraft1.20.2, somente cache local | https://www.minecraft.net/en-us/usage-guidelines / https://resources.download.minecraft.net | Mojang/Microsoft, direitos reservados; uso condicionado às Guidelines em vídeo original.27OGGs/18eventos, SHA1 fixos. NãoCC0; não redistribuir os arquivos isolados. Ver [NATIVE-SOUND.md](NATIVE-SOUND.md). |
| faster-whisper1.2.1 | https://github.com/SYSTRAN/faster-whisper | MIT, inferência CPU |
| Whisper/pesos convertidos | https://github.com/openai/whisper / https://huggingface.co/mobiuslabsgmbh/faster-whisper-large-v3-turbo | MIT indicada no model card; cache local |
| Wav2Vec2 português ONNX quantizado | https://huggingface.co/onnx-community/wav2vec2-large-xlsr-53-portuguese-ONNX | Apache-2.0 indicada no model card; alinhamento CTC local, pesos em cache privado |
| CTranslate2/PyAV/NumPy/Pillow/jsonschema | Pacotes oficiais PyPI, versões em requirements.lock | Licenças próprias dos distribuidores; não confundir com os assets |
| Pixelify Sans | https://github.com/google/fonts/tree/main/ofl/pixelifysans | SIL OFL1.1, OFL.txt preservado junto da fonte; SHA256 9ba86cd010a4de309d263ceff8e8044092c9db7efda869620cb9ff1c4389e8a5 |
| llama.cpp opcional | https://github.com/ggml-org/llama.cpp/releases/tag/b11982 | MIT, binário oficial CPU Linuxx64; SHA256 a7e6cc16d423fc88c204a8d8e646c1d11b1d0de9ec4a56942f6c02936e9bf09c |
| Qwen2.5-1.5B-Instruct-GGUF opcional | https://huggingface.co/Qwen/Qwen2.5-1.5B-Instruct-GGUF | Apache2.0, revisão91cad51170dc346986eccefdc2dd33a9da36ead9; SHA2566a1a2eb6d15622bf3c96857206351ba97e1af16c30d7a74ee38970e434e9407e |
| Piper1.8.0, apenas testes | https://github.com/OHF-Voice/piper1-gpl | GPL3; não usado para regravar narração do usuário |
| Voz pt_BR-faber-medium, apenas testes | https://huggingface.co/rhasspy/piper-voices/blob/main/pt/pt_BR/faber/medium/MODEL_CARD | Dataset CC0 conforme card; SHA e rótulo sintético no manifesto de teste |
| eSpeak NG1.52, teste antigo | https://github.com/espeak-ng/espeak-ng | GPL3; pacotes Debian extraídos localmente sem instalação administrativa |

Os downloads opcionais ficam em `.tools`/`.models`, excluídos do Git. Bootstrap verifica SHA256 e extrai o tar com filtro de caminhos. Não instala MCPs de terceiros nem abre um servidor para a rede externa. O servidor local opcional escuta apenas em127.0.0.1.

Codex nesta conversa usa o plano já contratado e os limites dele. Não é uma licença de API paga nem capacidade ilimitada. O projeto não lê arquivos de credenciais e não contorna autenticação.
