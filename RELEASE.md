<p align="right">
  <b>🇧🇷 Português</b> | <a href="RELEASE.zh-CN.md">🇨🇳 简体中文</a>
</p>

# Release Checklist

## Importe ou atualize nova versão de materiais
```bash
python3 scripts/import-350.py "/path/to/350张瑞士平面图片"
```

O script verifica de 001 a 350 números consecutivos, copia imagens HD, gera miniaturas leves e reconstrói CSV, JSON e galerias de 8 categorias. É seguro reexecutar; imagens inalteradas não serão processadas novamente.
## Liberar versão do GitHub
1. Confirme se `python3 scripts/verify-collection.py` foi aprovado.2. Empacote `v2/images/` em `dist/350-layout-compositions-images.zip`.3. Envie e envie o código e as imagens.4. Crie uma nova versão, lance e carregue dois ZIPs da nova versão e da versão clássica:   - `350-layout-compositions-images.zip`
   - `100-layout-compositions-images.zip`
5. Verifique a entrada da categoria README, links de imagens e dois anexos de download.
O ZIP é publicado apenas como um anexo de versão do GitHub e não está comprometido com o histórico do Git.