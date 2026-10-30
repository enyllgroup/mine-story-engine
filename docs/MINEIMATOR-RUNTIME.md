# Mine-imator: instalação e teste real do runtime

Instalação: 29/10/2026; exportação e inspeção: 30/10/2026. Objetivo: iniciar o Mine-imator real e fornecer
um binário oficial ao teste de animação/exportação. Nenhum Blender substituto foi
utilizado. Instalar o programa não equivale a concluir a produção de um vídeo.

## Fonte e versão instaladas

- Site oficial: https://www.mineimator.com/download
- Download oficial Linux: https://www.mineimator.com/dl/mineimator-2.0.2-tar
- Versão anunciada: **2.0.2**, publicada em 12/11/2023.
- Arquivo baixado: `.tools/mineimator/mineimator-2.0.2.tar.gz` (36.218.397 bytes).
- SHA256: `b3e3508008a201dc5daf6f42506bdbf24735a870132e028ef2e53b5bff379a09`.
- Executável extraído sem alteração:
  `.tools/mineimator/official/Mine-imator/Mine-imator`.
- Recursos Minecraft incluídos pelo pacote oficial:
  `Data/Minecraft/1.20.2.zip` e `Data/Minecraft/1.20.2.midata`.

O programa e seus recursos externos ficam em `.tools`, excluída do Git. Não são
redistribuídos como parte do código MineStory. O instalador reproduzível é:

```bash
python scripts/install_mineimator.py
```

O script verifica o SHA256 antes da extração, não usa privilégios administrativos
e não altera o mecanismo de Trial/Full. A extração usa filtro de segurança de
caminhos do `tarfile` (ambiente testado: Python 3.12.14).

## Verificações executadas

1. `file` identificou um executável **ELF64 x86-64** para Linux.
2. `ldd` não informou bibliotecas ausentes. O pacote já fornece suas bibliotecas
   auxiliares em `Data/Libraries`; Qt não precisou ser compilado.
3. A execução com `QT_QPA_PLATFORM=offscreen` falhou com código134. Mensagem
   concreta: plugin Qt `offscreen` não encontrado; único plugin disponível: `xcb`.
   Portanto a versão oficial testada precisa de um display X, ainda que virtual.
4. Depois disso, o agente principal iniciou o binário oficial com Xvfb em
   `DISPLAY=:99`, usando `LIBGL_ALWAYS_SOFTWARE=1`. Inspeção de janela, abertura
   de projeto e exportação são tratadas no teste principal, não presumidas aqui.

Exemplo do início, após instalar/configurar Xvfb localmente:

```bash
cd .tools/mineimator/official/Mine-imator
DISPLAY=:99 LIBGL_ALWAYS_SOFTWARE=1 ./Mine-imator
```

O pacote oficial é uma aplicação gráfica; o teste `--help` não comprovou nenhuma
CLI de exportação. Não afirmar API ou modo headless inexistente/funcional sem
testar especificamente a integração.

## Fonte consultada e compilação não necessária

O repositório oficial foi clonado para auditoria, sem executar seu instalador:
https://github.com/stuffbydavid/Mine-imator

Commit: `eda12dd0db7cb5892fc068491c60259dba0aa154`, de 12/09/2026.
`BUILD.md` e `Setup.sh` descrevem Qt5.15.19, CMake, clang/OpenMP e bibliotecas
externas. O caminho `qmake` neste host era apenas um wrapper e falhava porque
`/usr/lib/qt5/bin/qmake` não existe. Esses requisitos de build foram evitados
porque o binário Linux oficial já pôde ser instalado.

O GitHub não apresentou releases na API e `/releases/latest` respondeu404.
Isso **não** significava ausência de download Linux: o download está no site
oficial. A página oficial fornece `.deb` e `.tar`.

## Custo e condições observadas

Página oficial consultada: https://www.mineimator.com/upgrade

Ela informa que a versão **Trial pode exportar filmes/imagens com watermark**.
Para exportar sem essa marca, a versão Full usa uma chave recebida pelo próprio
site. A doação é explicitamente **opcional**, com a opção “I'd rather not donate”.
Não se trata de autorização para gerar uma chave local, alterar `trial_version`,
modificar o executável ou remover marca imposta pela versão Trial no vídeo.

Os arquivos `GmProject/options/windows/License.txt` e
`GmProject/options/windows/installer/license.txt`, no fonte oficial, contêm EULA
GameMaker permitindo instalação/uso pessoal e comercial sob suas condições e
proibindo modificação, redistribuição e engenharia reversa da aplicação. Essa
observação não é uma licença geral para distribuir código modificado do projeto.

As páginas oficiais de download/upgrade e o pacote examinado não solicitaram uma
conta Minecraft para abrir o programa. Isso não substitui regras de uso dos
recursos Minecraft nem garante direitos além dos termos de seus proprietários.

**Resultado:** o binário oficial foi ativado em Full pelo fluxo gratuito oficial
“I'd rather not donate”, sem modificar o executável nem remover watermark por
edição. Exportou 600 quadros/20 segundos em 1080×1920/30 FPS. O master foi
confirmado por log nativo e ffprobe, e a montagem de 17,95 segundos foi inspecionada.
O render levou 431 segundos em Mesa llvmpipe; não há GPU física neste host.
Consulte [a validação e seus limites](MINEIMATOR-VALIDATION.md). Nenhuma chave de
ativação ou recurso Minecraft externo foi incluído no Git.
