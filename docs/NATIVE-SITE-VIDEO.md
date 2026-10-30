# Publicar um único vídeo no Site existente

Depois da revisão do vídeo final, prepare uma pasta nova, sem alterar o arquivo
MP4:

```bash
.venv/bin/python scripts/stage_video_site.py \
  --video productions/NOVO_JOB/video_final.mp4 \
  --output scratch/site-video-NOVO_JOB
```

O helper verifica H.264/AAC, duração e SHA256. Até 20 MiB, fornece o próprio
MP4 como asset. Arquivos maiores são divididos em partes de até 20 MiB e reunidos
no navegador em um Blob **idêntico ao arquivo original**; não há uma segunda
codificação nem outro vídeo. A interface tem somente player e download. Para
arquivos grandes, é preciso carregar todas as partes antes de reproduzir, usando
memória do navegador proporcional ao tamanho do vídeo.

Use a skill Sites para atualizar o projeto privado existente, preservando a
configuração de acesso e as versões antigas. Copie a pasta preparada para a
pasta estática do checkout e publique uma nova versão do mesmo Site; não criar
um Site por produção. Não publique resultados que ainda falharam na inspeção.
A página funciona offline no teste com um mock das requisições; um teste de
navegador real ainda depende da infraestrutura de preview disponível.
