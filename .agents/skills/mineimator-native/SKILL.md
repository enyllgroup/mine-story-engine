---
name: mineimator-native
description: Install and operate the official Mine-imator Linux GUI with native project files, Xvfb, and inspected mouse/keyboard automation.
---

# Mine-imator nativo

Use esta skill para cenas e testes **no Mine-imator real**. Não encaminhe o
trabalho para o renderer Blender legado. A direção visual é realizada pelo modelo
ativo do Codex; nenhuma API faturada é necessária.

## Comandos executáveis

Execute na raiz `mine-story-engine`:

```bash
python scripts/install_mineimator.py
python scripts/install_mineimator_x11.py
python scripts/mineimator_gui.py start
python scripts/mineimator_gui.py status
python scripts/mineimator_gui.py screenshot productions/inspecao-001.png
```

Os instaladores baixam fontes oficiais, verificam SHA256 e extraem os arquivos
localmente em `.tools`. O pacote X11 está fixado para Debian13 x86-64 e usa as
bibliotecas compartilhadas do host; não é um instalador universal. Ele não executa
scripts de manutenção Debian e não exige root. Para verificar downloads já presentes:

```bash
python scripts/install_mineimator_x11.py --verify-only
```

O controlador usa `:100` por padrão. `--display :99` permite interagir com uma
sessão existente, mas não transfere sua propriedade ao controlador. `start`
recusa substituir uma tela em uso. `stop` encerra somente grupos de processos
iniciados pelo controlador e cuja identidade de PID/starttime ainda corresponde
ao registro local. Não inicie duas instâncias simultâneas sem necessidade:
o Mine-imator mantém suas configurações no diretório de usuário.

Interaja após inspecionar uma captura real; coordenadas dependem do tamanho da janela:

```bash
python scripts/mineimator_gui.py click 960 555
python scripts/mineimator_gui.py key ctrl+o
printf '%s' '/caminho/absoluto/teste.miproject' | python scripts/mineimator_gui.py text
python scripts/mineimator_gui.py key Return
python scripts/mineimator_gui.py open-project productions/teste.miproject
python scripts/mineimator_gui.py stop
```

Cliques mantêm o botão por0,4segundo e teclas por0,2segundo para que a interface,
que consulta o estado de entrada por frame, consiga recebê-los sob renderização
por CPU. `text` lê stdin e usa a seleção CLIPBOARD de X11 através do Tkinter,
mantendo a janela proprietária viva por3segundos e atendendo pedidos de seleção
enquanto o Mine-imator recebe Ctrl+V. `text --method typed --delay 100` é um
fallback, sujeito à perda de caracteres na interface sob carga. `open-project`
também usa clipboard. Não passe chaves de ativação como argumentos nem as
inclua em capturas, logs, commits ou arquivos publicados.

`open-project` exige o seletor de arquivos nativo com título `Open project`
antes de colar o caminho. Se houver confirmação de alterações ou outro popup,
o comando para e pede inspeção; ele não escolhe descartar ou salvar sozinho.
Confirme a escolha apropriada na interface e tente novamente. Para outra língua,
use `--dialog-title` com o título correspondente. A abertura só é reportada como
concluída se **novas linhas** do log nativo registrarem o caminho solicitado e
depois `Project loaded`. Logs antigos não aprovam uma nova tentativa.
O Return do seletor é mantido por0,03segundo para evitar que vaze para a timeline
e inicie a reprodução. `--log` e `--timeout` configuram a evidência e o prazo.

## Contrato e limites

- O binário oficial permanece sem alterações. Recursos Minecraft são os incluídos
  pelo programa; não redistribuir seu pacote ou as texturas no repositório.
- `.miproject` é o formato nativo JSON. Projetos gerados devem ser realmente
  abertos no Mine-imator e inspecionados; um JSON válido não prova execução.
- Não há CLI/API de exportação automática validada. Use o comando nativo de
  exportação de filme pela GUI, escolha câmera, intervalo, resolução e formato,
  confira o arquivo efetivo com ffprobe e inspecione frames de vários instantes.
- A Trial insere watermark. A opção gratuita de chave Full fica no fluxo oficial
  de upgrade com doação opcional. Não modificar flags, criar chaves ou remover
  watermark por edição do vídeo.
- Não declarar qualidade aprovada com base apenas em instalação, logs ou presença
  de arquivos. Confirmar personagens enquadrados, texturas presentes, atuação e
  progressão visual em frames reais.
- Preserve produções anteriores. Próximo teste autorizado: **um vídeo de cerca de
  20segundos**. Sites deve mostrar apenas esse vídeo, sem pacotes nem relatórios.
- Sem placa gráfica física neste ambiente, `LIBGL_ALWAYS_SOFTWARE=1` usa Mesa
  llvmpipe. Registre tempo real de exportação e limitações, sem prometer desempenho
  de GPU. Ausência de dispositivo de áudio não impede montagem posterior com FFmpeg.
