# Validação real do renderizador

Data: 2026-10-29. Blender 4.3.2, Workbench por EGL/Mesa em CPU; 3 CPUs,
cerca de 10 GB de RAM, nenhuma GPU física exposta. Esta inspeção descreve
artefatos efetivamente produzidos. Não equivale a aprovação editorial de
qualquer narração futura nem a certificação de estética vanilla idêntica.

## Evidências inspecionadas

| Artefato local | Verificação executada | Resultado |
|---|---|---|
| `productions/render_smoke/model_world_object_test.mp4` | Render real de 120 PNGs e codificação H.264; amostras antes/depois da caminhada, objeto e reação | Animação de 4 s efetiva, não slideshow |
| `productions/render_smoke/still.png` | Inspeção visual do personagem, carta, segundo personagem, casa, mesa e baú | Texturas presentes, enquadramento preservado |
| `productions/render_smoke_corrected/still.png` | Novo render após ajuste da posição da carta na mão e remoção de conflitos da pose idle | Carta acompanha mão na amostra; não é validação completa de todos os movimentos |
| `productions/cartas_preview/video_preview.mp4` | Decodificação com FFmpeg, FFprobe e 12 amostras, uma por cena | MP4 H.264, 360×640, 30 fps, aproximadamente 70,47 s, áudio AAC |
| Mesmo vídeo, de 65,7 a 70 s | Oito amostras da entrega/recepção e reação | A carta passa visualmente de Lia para Noa; existem aproximações de contato e orientação |
| `productions/cartas_final/preflight/**/still.png` | Inspeção das 12 cenas após correções do ambiente | Banca, ouro sem pictograma indevido e chão estendido aparecem nos renders novos |
| `productions/sol_preview/preflight/**/still.png` | Inspeção das sete cenas | Planetas em blocos, Sol, partículas, cama e objeto subterrâneo são diferentes dos assets do tema cartas |
| `.cache/scenes/4a4bd08c0e3a4bd949de9b016c646ddcb963595e13f5f900e67fa3864396e9a1/frames/frame_0060.png` | Inspeção do PNG e metadados | Render nativo de 1080×1920, não ampliação do preview; personagem, baú e cartas íntegros |

As produções completas finais podem terminar depois desta inspeção. O estado
atual e as medições definitivas são os de `production_report.json` e do relatório
de QC de cada job. Um PNG final isolado não prova a conclusão de um MP4 final.

## Teste A — personagem e atuação

Foi criado um personagem original com dimensões de cabeça 8×8×8, tronco
8×12×4, braços e pernas 4×12×4, usando 1/16 m por pixel. O personagem tem
pivôs independentes de cabeça, braços e pernas; a roupa e a face são próprias.
O teste executou caminhada, elevação do braço, ligação da carta à mão e reação
corporal com partícula de exclamação. Um segundo personagem aponta e comemora.

O teste cobre uma composição concreta de ações. Não comprova que todas as
combinações de correr, pular, sentar, cair, medo e transferências entre vários
atores estejam livres de interpenetração. A atuação é rígida e estilizada;
não há solução física de contato ou IK automático de dedos/cotovelo.

## Teste B — ambiente procedural

O cenário foi montado programaticamente com grama, terra, pedra, madeira,
troncos, folhas, casas e objetos. Cada face de bloco usa uma imagem pixelada
com filtro nearest. Não foram usadas texturas PBR, superfícies arredondadas
suaves ou arquivos de jogo extraídos. O render roda sem launcher Minecraft,
autenticação do jogo, interface gráfica ou add-ons de terceiros.

A primeira prévia longa revelou a borda finita do chão na parte inferior de
várias cenas. Os preflights posteriores e o PNG nativo inspecionado mostram
o chão ampliado. A prévia anterior permanece preservada como produção antiga;
não deve ser apresentada como prova de que essa correção já existia nela.

## Teste C — objeto personalizado e interação

A carta original é feita de cuboides com borda, ilustração em pixels de uma
criatura própria e linhas gráficas. Ela não contém arte ou logotipo Pokémon.
Foi gerada como objeto animável, exibida, segurada e comparada a outras cartas.
Os modelos `.bbmodel` editáveis da biblioteca são JSONs verificáveis; o pipeline
não depende de abrir manualmente o Blockbench.

A sequência de entrega é compreensível nas imagens, mas a carta flutua durante
parte do gesto e muda de orientação rapidamente. O código possui intervalos de
influência e deslocamento para a troca; isso ainda não é uma solução universal
de contato de mão. Interações futuras precisam de inspeção das cenas afetadas.

## Teste E — diversidade visual

O tema cartas produz feira, colecionadores, comparação de estado de conservação,
moedas e um laboratório. O tema desaparecimento do Sol produz espaço, planetas,
sequências de partículas, uma cama e uma construção subterrânea. Os assets e
acontecimentos não são o mesmo template com o texto trocado.

Há repetição editorial na demonstração de cartas: 11 das 12 cenas reutilizam a
mesma feira e câmeras próximas. A biblioteca e os cuboides abertos permitem mais
variação, mas a possibilidade técnica não prova que o diretor já atinja variedade
suficiente em toda produção. O céu espacial e as ilhas são representações
estilizadas; não simulam astronomia fisicamente.

## Fidelidade e problemas observados

- A linguagem de blocos, as proporções e a amostragem de pixels são compatíveis
  com o estilo Minecraft. As texturas são originais; o resultado não usa os
  recursos gráficos oficiais e não deve ser anunciado como vanilla idêntico.
- Sombras projetadas e efeitos de cavidade foram desativados. O padrão usa
  iluminação simples por normais e cores legíveis, sem shaders cinematográficos.
- No preflight de `sol_preview/scene_005`, a grama continua visualmente clara,
  embora a cena seja denominada `night`. O enquadramento não mostra o céu e a
  exposição configurada não torna a noite inequívoca. Esse ponto requer direção
  ou iluminação adicional antes de afirmar que a escuridão foi demonstrada.
- As faces têm poucos detalhes animados. Emoção depende principalmente de braços,
  cabeça, pulos e partículas. Não existe lip sync, que não é necessário para a
  narração externa.
- Metadados de projeção amostram cinco instantes por cena. Eles detectam limites
  de quadro, mas não provam visibilidade contínua, ausência de oclusão, naturalidade
  de movimento ou correção semântica.
- Na primeira prévia, as moedas e partículas de ouro herdavam uma textura de carta.
  Os preflights corrigidos exibem ouro limpo. Não confundir versões dos artefatos.

## Desempenho observado

O smoke de 120 frames a 270×480 levou aproximadamente 17,4 s para renderizar,
com concorrência de outras tarefas. Frames simples aquecidos ficaram próximos
de 0,08–0,11 s. A construção passou a usar datablocks compartilhados, evitando
uma chamada de operador Blender para cada bloco.

Três frames nativos a 1080×1920 do mesmo cenário levaram aproximadamente 3,27 s
sem sombras/cavidade; frames seguintes ficaram em torno de 0,93–0,96 s naquele
ensaio. O primeiro render com sombras/cavidade levou aproximadamente 5,45 s nos
três frames. Esses números são medições de cenas específicas, não uma promessa
de tempo para 70 s completos; resolução, número de objetos e concorrência mudam
o custo. O relatório de produção mede o job real.

## Reprodução mínima

```bash
python scripts/render_smoke.py
blender -b --threads 2 --python minestory/blender_scene.py -- \
  --scene examples/render_smoke.json --output productions/smoke_novo \
  --width 270 --height 480 --fps 30 --frames 120 --resume --save-blend
ffmpeg -framerate 30 -i productions/smoke_novo/frame_%04d.png \
  -c:v libx264 -pix_fmt yuv420p -crf 20 productions/smoke_novo/teste.mp4
```

Escolha sempre um diretório novo. Para a pipeline de áudio completa, incluindo
legendas, efeitos e relatório de QC, use os comandos em `OPERATIONS.md`.
