# Pesquisa técnica e decisão de arquitetura

Verificação: **29/10/2026**, ambiente Linux x86-64, 3 CPUs, ~10 GB RAM, sem GPU exposta. Evidências estruturadas, hashes, datas e comandos: [research-evidence.json](research-evidence.json). As conclusões abaixo distinguem documentação/código inspecionado de execução real. Uma descrição de repositório não foi tratada como teste.

## Decisão

Adotar **Blender com Python em background**, um compilador próprio de cenas declarativas, assets originais de proporções compatíveis com Minecraft, ASR local e montagem com FFmpeg. O Blender já instalado evita acrescentar um jogo licenciado e uma cadeia de automação de interface. O JSON de cenas deve continuar independente do renderizador, permitindo um futuro backend Java sem refazer transcrição, direção, sincronização e biblioteca.

Esta decisão demonstra uma rota de automação; **não demonstra por si só fidelidade vanilla aprovada**. Texturas originais podem se aproximar da linguagem visual, mas não são os pixels oficiais. O resultado precisa ser comparado visualmente com os critérios do projeto. Não incluir texturas/skins oficiais ou MCprep bundled assets sem a licença e os direitos correspondentes. Não contornar login ou comprar componentes.

Fontes: [CLI Blender](https://docs.blender.org/manual/en/4.3/advanced/command_line/render.html), [licença/uso dos assets MCprep](https://github.com/Moo-Ack-Productions/MCprep/blob/master/README.md), [diretrizes Minecraft](https://www.minecraft.net/en-us/usage-guidelines).

## Comparação das três rotas

Os valores são avaliações de engenharia, não medições de desempenho. `A` depende de um cliente Minecraft Java licenciado e autenticado. `B` depende da validação de uma interface de exportação. `C` permite usar apenas recursos gratuitos originais.

| Critério | A — Minecraft Java | B — Mine-imator | C — Blender + compilador |
|---|---|---|---|
| Fidelidade vanilla | Máxima, por usar o jogo e recursos oficiais | Forte com assets adequados | Depende de UV, texturas, proporções, iluminação e câmera; exige inspeção |
| Controle por código | Fabric + comandos + bridge próprio | Projeto JSON verificável; render batch não demonstrado | API Python e render background documentados e disponíveis |
| Áudio → vídeo completo | Requer orquestrador e captura no cliente | Requer geração de projeto e acionamento de exportação | Um processo Python pode gerar, animar, renderizar e chamar FFmpeg |
| Liberdade de animação | Vanilla limita articulação; displays/mods ampliam | Editor dedicado com hierarquia/timeline | Hierarquia, keyframes e geometria livres |
| Construção procedural | Muito boa: comandos, structures, WorldEdit, data packs | Importação de mundos; schema próprio precisa ser mantido | Geometria e blocos gerados diretamente, sem arquivo de mundo intermediário |
| Reutilização/cache | Structures/resource packs/replays | Assets e projetos | Biblioteca, hash de cena, .blend e segmentos por cena |
| Velocidade | Potencial alto em cliente com aceleração; não medido aqui | Não medida aqui | Backend simples deve ser medido; CPU não equivale a tempo real |
| Estabilidade para automação | Sensível às versões Java/Fabric/mod/client | Compatibilidade do projeto/export ainda não validada | Blender 4.3.2 já presente; fixar versão e testar o compilador |
| Custo obrigatório nesta sessão | Não há licença de jogo fornecida | Download pode ser gratuito, termos precisam ser conferidos | Nenhuma licença paga necessária |
| Risco principal | Licenciamento, sessão gráfica, relógio do jogo/captura | Interface e licença, não apenas formato do projeto | Fidelidade e qualidade artística não vêm automaticamente da ferramenta |

Uma arquitetura híbrida só é útil se remover uma limitação medida. Acrescentar Minecraft, Blockbench GUI, MCprep e Blender ao mesmo fluxo inicial aumentaria o número de versões, processos e pontos de falha sem comprovar ganho proporcional.

## Minecraft Java, Fabric e construção

- **Fabric API** é mantida, Apache-2.0; a branch padrão observada é `26.3`. A documentação oficial contém comandos de cliente/servidor, networking, eventos, renderização e geração de dados. Usar a versão correspondente do jogo; nunca presumir que um exemplo 1.21 funciona sem alteração em 26.3. [Fabric Docs](https://docs.fabricmc.net/develop/), [fonte](https://github.com/FabricMC/fabric-api).
- **Data packs** permitem funções, eventos e comandos temporizados. **Resource packs** fornecem texturas/modelos e linguagem visual; não substituem um renderizador de vídeo. **Display Entities**, disponíveis desde Java 1.19.4, têm transformações e interpolação. São úteis para compor rigs com peças/item displays. Ticks do servidor e frames de vídeo são relógios distintos; uma implementação precisa mapear segundos, ticks e amostragem de câmera. [Notas oficiais 1.19.4](https://www.minecraft.net/en-us/article/minecraft-java-edition-1-19-4).
- **WorldEdit**: licença GPL-3.0 verificada em `LICENSE.txt`; branch `version/7.4.x` ativa. EditSession, schematics, `//generate` e CraftScripts são interfaces reais para construção. CraftScripts exigem Rhino e executam JavaScript dentro do servidor; não são um exportador de vídeo. Não instalar o runtime adicional se a construção puder ser feita no backend escolhido. [API e comandos](https://worldedit.enginehub.org/en/latest/commands/), [CraftScripts](https://worldedit.enginehub.org/en/latest/usage/other/craftscripts/).

Uma futura integração Java deve implementar um controlador próprio: receber JSON validado, construir chunks/structures, gerar os atores de displays ou entidades, atualizar poses por tempo absoluto, definir câmera de cliente e capturar frames determinísticos. Apenas enviar comandos por RCON não permite controlar toda a câmera do cliente nem garante frames corretos. Esse backend **não foi implementado ou validado pela pesquisa**.

## Flashback e Replay Mod: exportação verificada com limites

### Flashback

Código consultado no commit `bf046b763ddf466bdc1b6d9c6cc7ba06e527f3e2`, mensagem de versão **0.43.6**. A classe `ExportSettings` contém resolução, ticks inicial/final, FPS, codecs e destino. `ExportJob`, `ExportJobQueue` e janelas de exportação existem. A inscrição de comandos em `Flashback.java` mostra `start`, `finish`/`end`, `pause`, `unpause`, `config` e `mark`; **não foi encontrado um comando de exportação nessa inscrição**. Isso não prova a ausência de qualquer interface interna em todo o projeto, mas impede prometer uma CLI estável de exportação já pronta.

`LICENSE.md` é explícito: **All rights reserved; do not redistribute**. Somente as localizações têm CC BY 4.0. Código público não torna Flashback open source. Não embutir o mod nem redistribuir um derivado supondo permissão. Um bridge independente exigiria avaliar a interface, seus termos e a compatibilidade de versão.

Fontes: [Flashback.java](https://github.com/Moulberry/Flashback/blob/bf046b763ddf466bdc1b6d9c6cc7ba06e527f3e2/src/main/java/com/moulberry/flashback/Flashback.java), [ExportSettings](https://github.com/Moulberry/Flashback/blob/bf046b763ddf466bdc1b6d9c6cc7ba06e527f3e2/src/main/java/com/moulberry/flashback/exporting/ExportSettings.java), [licença](https://github.com/Moulberry/Flashback/blob/bf046b763ddf466bdc1b6d9c6cc7ba06e527f3e2/LICENSE.md).

### Replay Mod

Commit consultado `13ca34329be20fd3f3d2b2ccb4512c7d3f028871`, release **2.6.28**; GPL-3.0-or-later. Documentação confirma keyframes de posição/tempo, interpolação e exportação por FFmpeg no cliente. O README declara que o mod não fornece uma API externa. **Command Line Settings** na documentação se refere ao executável/argumentos do **FFmpeg**, não a uma CLI standalone do Replay Mod capaz de abrir e renderizar replays sem cliente.

É um candidato futuro melhor para um bridge redistribuível do que depender de código Flashback sem licença aberta; essa é uma inferência de licença, não teste de compatibilidade. Exigiria iniciar cliente legítimo, integrar timeline/exportação e testar saída. [README](https://github.com/ReplayMod/ReplayMod/blob/13ca34329be20fd3f3d2b2ccb4512c7d3f028871/README.md), [documentação](https://www.replaymod.com/docs/).

## Mine-imator

O upstream atual **não deve ser descartado como Windows-only ou abandonado**. README e BUILD documentam o projeto GML convertido para C++/Qt e builds Windows, macOS e Linux. No snapshot, a branch é `master`, commit `eda12dd0db7cb5892fc068491c60259dba0aa154`. `pushed_at` do repositório e data do commit padrão são coisas diferentes: o primeiro pode mudar por outras branches/tags.

O código `project_load.gml` lê `.miproject` JSON desde o formato 1.1.0; `project_save_project.gml` grava resolução, timeline e câmera. Isso torna geração programática plausível. `render_start.gml` é função interna e `AppHandler.cpp` inicia `QApplication`; **não foi demonstrado um contrato suportado de batch render sem GUI**. Seria necessário validar um binário ou criar um bridge, não apenas escrever JSON.

A API GitHub não identifica uma licença global do repositório. Há uma EULA GameMaker no instalador com restrições de modificação e redistribuição; ela não deve ser interpretada automaticamente como licença de todo o fonte. Não se concluiu que o projeto é open source. Essa incerteza e o esforço de integração tornam a rota menos adequada à entrega gratuita/autônoma neste ambiente.

Fontes: [README](https://github.com/stuffbydavid/Mine-imator/blob/eda12dd0db7cb5892fc068491c60259dba0aa154/README.md), [build Linux](https://github.com/stuffbydavid/Mine-imator/blob/eda12dd0db7cb5892fc068491c60259dba0aa154/BUILD.md), [project_load](https://github.com/stuffbydavid/Mine-imator/blob/eda12dd0db7cb5892fc068491c60259dba0aa154/GmProject/scripts/project_load/project_load.gml), [EULA bundled](https://github.com/stuffbydavid/Mine-imator/blob/eda12dd0db7cb5892fc068491c60259dba0aa154/GmProject/options/windows/installer/license.txt).

## Modelagem, rigs e integrações

| Ferramenta | Evidência observada em 29/10/2026 | Uso/restrição para MineStory |
|---|---|---|
| [Blockbench](https://github.com/JannisX11/blockbench/releases/tag/v5.2.2) | 5.2.2, 08/10/2026; GPL-3.0; API JavaScript de plugins | Editor opcional para `.bbmodel`. Modelos criados são do autor; não é necessário manter Electron aberto para compilar cuboides em Blender. |
| [Animated Java](https://github.com/Animated-Java/animated-java/releases/tag/v1.11.0) | 1.11.0, 09/10/2026; arquivo LICENSE é AGPL-3.0-or-later; suporta MC26.3 | Exporta resource/data packs, funções e animações. Não gera automaticamente vídeo final. Versão1.11 altera schema JSON: exige adapter versionado. |
| [BetterModel](https://github.com/toxicity188/BetterModel/releases/tag/3.6.0) | 3.6.0, 27/10/2026; MIT; API Kotlin/Java; Paper e Fabric | Item displays, animação, Molang, IK e resource pack. README atual requer Java25 e MC1.21.4–26.3. Não é renderizador MP4; depende do cliente. |
| [Blockbench Import Library](https://github.com/tomalbrc/blockbench-import-library) | 2.2.0+26.3-rc-3; LGPL-3.0; commit e04a30a | Importa bbmodel/ajmodel, Polymer, item displays; comando `/bil model` e API loaders. Bom candidato Java futuro; não elimina licença do cliente/captura. |
| [MCprep](https://github.com/Moo-Ack-Productions/MCprep/releases/tag/3.6.3) | 3.6.3, 12/07/2026; release declara Blender2.83–5.2; GPL-3.0 | Facilita importação/material/rigs. README antigo é menos atualizado que o release. Assets bundled exigem Minecraft legal; rigs têm atribuições próprias. Não é necessário para geometria original procedural. |
| [Blender](https://www.blender.org/about/license/) | Instalado4.3.2; API Python/background executada | Montagem procedural, hierarquia, UV nearest, poses e render por cena. Usar materiais simples, flat faces, sem PBR/cinema padrão. Licença da ferramenta não transfere automaticamente licença a assets importados. |

[Blockbench plugin API](https://www.blockbench.net/wiki/docs/plugin/) é documentada e permite criar adaptadores. Para não adicionar uma GUI à etapa de render, um subconjunto explícito de `.bbmodel` pode ser lido diretamente, preservando cuboides, hierarquia, pivôs, UV e animação onde implementados. Um adapter não deve declarar suporte a mesh/IK/Molang completo sem testes. Formatos e recursos não suportados precisam produzir diagnóstico em vez de desaparecer silenciosamente.

## MCPs Blockbench e Blender

Dois projetos reais foram encontrados: [RenasDemirbas/BlockBenchMCP](https://github.com/RenasDemirbas/BlockBenchMCP) e [jasonjgardner/blockbench-mcp-plugin](https://github.com/jasonjgardner/blockbench-mcp-plugin), ambos GPL-3.0 nos metadados. Não são produtos oficiais do Blockbench ou OpenAI. Repositórios/marketplaces de terceiros não foram tratados como garantia de segurança nem funcionamento.

RenasDemirbas **1.10.1**, 25/10/2026, documenta modelagem, texturas, animação, renders e `BB_HEADLESS=1`. O modo inicia Blockbench sob demanda; no Linux sem display exige um wrapper `xvfb-run`. Ocultar janela é Windows-only. Portanto não seria correto dizer que não tem headless; ele ainda depende do aplicativo/editor e de uma superfície gráfica virtual no Linux.

A política de segurança documenta que versões **até1.6.0** aceitavam conexões de qualquer site ao WebSocket local, com execução via `eval_code`. A correção de Origin começa em1.6.1; apenas1.10.x é suportada. O atual bridge continua deliberadamente capaz de executar JavaScript. Manter loopback, conferir versão e auditar scripts antes de instalar. Nenhum MCP foi instalado ou declarado testado por esta pesquisa. Para o backend escolhido, uma integração direta e restrita com o formato elimina essa dependência recorrente. [README/headless](https://github.com/RenasDemirbas/BlockBenchMCP/blob/a7b78170aab138188e7291fd3886a7252a260c4b/README.md), [SECURITY.md](https://github.com/RenasDemirbas/BlockBenchMCP/blob/a7b78170aab138188e7291fd3886a7252a260c4b/SECURITY.md).

Um MCP Blender de propósito geral também precisaria autorizar execução Python no editor. Para este projeto, chamar o Blender instalado com script próprio versionado é mais simples e permite auditar exatamente o que é executado. Não há benefício demonstrado em acrescentar um servidor MCP só para envolver a mesma API.

## Áudio, alinhamento, legendas e montagem

- [**faster-whisper**](https://github.com/SYSTRAN/faster-whisper): MIT, ativo; CPU com `compute_type="int8"`, VAD e `word_timestamps=True` são documentados. Bom candidato de custo/latência em3 CPUs. Benchmarks upstream não são medições deste hardware. Timestamps de ASR não são forced alignment fonético; não rotular como alinhamento forçado se este não foi executado. Modelo e transcrição precisam ser cacheados pelo hash do áudio/configuração.
- [**WhisperX**](https://github.com/m-bain/whisperX): BSD-2-Clause na versão consultada; usa ASR, VAD e alinhamento wav2vec2 específico por idioma. É uma alternativa real quando se precisa de precisão adicional; instalação CPU é suportada. Torch/torchaudio e pesos extras aumentam espaço/memória. Não ativar diarização para narrador único: acrescenta dependências e pode exigir token/termos dos modelos. Pesos têm licença própria, diferente da biblioteca.
- [**FFmpeg**](https://ffmpeg.org/ffmpeg-filters.html): instalado7.1.5 com libass/libx264 e build GPL. `ass/subtitles` permite legendas editáveis com palavra ativa; `amix` e `sidechaincompress` permitem efeitos abaixo da narração; `blackdetect` e `freezedetect` ajudam no QC. `loudnorm` altera nível: usar apenas se configurado; nunca esticar/substituir a voz. H.264/AAC exigem checagem de stream, FPS, proporção e duração com ffprobe.
- [**OpenCV**](https://github.com/opencv/opencv): candidato a inspeção de frames e diferenças; não identifica sozinho semântica narrativa. Para distribuição simples, PIL/NumPy e FFmpeg cobrem vários diagnósticos sem instalar OpenCV. Checagens de frame preto/estagnação não equivalem a aprovação artística ou de sincronismo de palavras.
- [**ASS/libass**](https://github.com/libass/libass): contorno, sombra e tags temporais por palavra suportam identidade própria, enquanto SRT preserva intercâmbio básico. Exportar ambas e testar rasterização real de acentos, limites da tela e duração. Definir região reservada para legendas no storyboard; UI das redes muda e não existe uma margem que garanta todos os aparelhos.

## Sons, fontes, direitos e custo

**Sons sintéticos originais** são a primeira opção: passos secos, impactos de blocos, aparição e transição gerados com osciladores/ruído/envelope evitam baixar pacotes desconhecidos. Catálogos externos devem registrar autor, URL, versão, licença e atribuição por arquivo; não presumir que todo Freesound é CC0. Música fica desativada por padrão. Não redistribuir sons ou música de Minecraft como se fossem livres. [Diretrizes oficiais sobre música](https://help.minecraft.net/hc/en-us/articles/21984449056781-Using-Minecraft-Music-in-Videos-and-Streams).

[Press Start2P](https://github.com/google/fonts/tree/main/ofl/pressstart2p) usa SIL OFL1.1, confirmada em `OFL.txt`; pode ser incluída com o aviso/licença. É muito larga para legendas longas: testar tamanho, acentos PT-BR e até poucas palavras por bloco. Não usar o logotipo Minecraft como marca do canal.

Nenhuma API paga é necessária para a arquitetura proposta. Um diretor pode usar **Codex CLI autenticado pelo plano ChatGPT existente**, sujeito à franquia do usuário, ou um modelo local gratuito. A autenticação local foi constatada, mas **não implica chamada de modelo bem-sucedida nem franquia ilimitada**. Uma assinatura Codex não deve ser tratada como autorização automática para consumo de API faturada separadamente. O modo local e o modo assistido precisam ser identificados no relatório; um fallback lexical não equivale a um diretor semântico livre.

Se a narração tiver menos de60s, emitir aviso sem alterar a duração. O programa TikTok possui outros requisitos além de duração e exige conteúdo maior que um minuto; renderizar65s não garante monetização. [TikTok oficial](https://support.tiktok.com/en/business-and-creator/creator-rewards-program/how-is-the-creator-rewards-program-different-from-the-tiktok-creator-fund).

## Skills oficiais Codex

Foi inspecionada a árvore oficial [openai/skills](https://github.com/openai/skills/tree/49f948faa9258a0c61caceaf225e179651397431), commit `49f948faa9258a0c61caceaf225e179651397431`, e lidos os guias `skill-creator`, `skill-installer`, `transcribe` e `screenshot`. No snapshot consultado, **não há skill oficial especializada em Minecraft, Blockbench, Blender, storyboard, motion design ou controle de câmeras**. Isso se refere ao catálogo consultado, não a todos os repositórios públicos existentes.

| Skill existente | Avaliação |
|---|---|
| `skill-creator` | Útil para estrutura, scripts e validação de skills próprias; não implementa animação. |
| `skill-installer` | Mecanismo oficial para baixar skills; não precisa baixar toda a coleção. |
| `transcribe` | O script chama a API OpenAI e requer `OPENAI_API_KEY`; excluída pela exigência de custo zero adicional. |
| `speech` | Não é necessária para preservar a narração do usuário; voz sintética só pode existir como fixture de teste. |
| `screenshot` | Captura desktop do sistema; não substitui inspeção dos frames do vídeo, e não agrega ao backend background. |
| `playwright` | Útil para testes de um launcher web eventual; não é motor de animação nem requisito inicial. |
| `render-deploy` | Deploy da plataforma Render, não renderização de vídeo; não confundir pelo nome. |

O CLI instalado é **0.163.0**. A [documentação oficial atual](https://learn.chatgpt.com/docs/build-skills) define descoberta no repositório por `.agents/skills`, usuário por `~/.agents/skills`, suporte a symlinks e `SKILL.md` com `name`/`description`. O guia antigo do instalador ainda menciona `~/.codex/skills`; para portabilidade, preferir skills locais versionadas no repositório. Skills adicionadas devem apontar a scripts que realmente existem e produzir os mesmos artefatos da CLI, sem duplicar a implementação em11 processos.

## Verificações efetivamente executadas por esta pesquisa

| Comando | Resultado real | Limite |
|---|---|---|
| `blender --version` |4.3.2 | Não mede qualidade nem FPS. |
| `blender --background --factory-startup --python-expr ...` | Importou `bpy`, informou background=true e terminou com exit0 | Comprova execução Python sem GUI, não uma produção animada. |
| `ffmpeg -version` |7.1.5, libass e libx264 presentes | Não é teste de muxagem final. |
| `ffmpeg -hide_banner -filters` |ass, subtitles, amix, loudnorm, sidechaincompress, blackdetect e freezedetect presentes | Funcionalidade disponível, não QC concluído. |
| `codex --version`, `codex exec --help` |0.163.0 e comando não interativo disponível | Não é teste do diretor. |
| `codex login status` | Logged in using ChatGPT | Não expôs credenciais; não prova requisição posterior. |

Minecraft Java, Fabric, Replay Mod, Flashback, Mine-imator, Blockbench GUI/MCP e MCprep **não foram iniciados/instalados durante esta pesquisa**. As verificações finais do projeto precisam usar os MP4s, frames, tempos e relatórios efetivamente gerados pelo pipeline. Não transportar uma avaliação de documentação para o status “teste aprovado”.
