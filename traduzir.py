import os
import re
import sys
import time
import json
import urllib.request
import urllib.parse

# Extensões de documentos de texto suportadas
EXTENSOES_PERMITIDAS = {'.md', '.txt'}

# Regex para detectar caracteres chineses (CJK Unified Ideographs)
CHINESE_REGEX = re.compile(r'[\u4e00-\u9fff]')

# Cache em memória para reutilizar termos repetidos e poupar requisições
CACHE_TRADUCAO = {}

def traduzir_trecho_api(texto, de='zh-CN', para='pt'):
    """Traduz um trecho de texto via endpoint seguro de tradução, com retentativas e cache."""
    if not texto or not texto.strip():
        return texto
    if texto in CACHE_TRADUCAO:
        return CACHE_TRADUCAO[texto]
    if not CHINESE_REGEX.search(texto):
        return texto

    url = f"https://translate.googleapis.com/translate_a/single?client=gtx&sl={de}&tl={para}&dt=t&q={urllib.parse.quote(texto)}"
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'})

    for tentativa in range(4):
        try:
            with urllib.request.urlopen(req, timeout=12) as resp:
                data = json.loads(resp.read().decode('utf-8'))
                resultado = ''.join(p[0] for p in data[0] if p and p[0])
                CACHE_TRADUCAO[texto] = resultado
                time.sleep(0.05)  # Rate limiting consciente
                return resultado
        except Exception as e:
            time.sleep(1 + tentativa)
            if tentativa == 3:
                print(f"  [Aviso] Falha ao traduzir trecho após 4 tentativas: {e}", flush=True)
                return texto
    return texto

def traduzir_linha_markdown(linha):
    """Traduz uma linha mantendo URLs, imagens, atributos HTML e códigos intactos."""
    if not CHINESE_REGEX.search(linha):
        return linha

    # Caso 1: Linha de galeria com imagens HTML: | <a href="..."><img ... alt="..."></a> |
    if '<img ' in linha:
        # Apenas traduz o valor do atributo alt="..."
        def repl_alt(m):
            val = m.group(1)
            if CHINESE_REGEX.search(val):
                return f'alt="{traduzir_trecho_api(val)}"'
            return m.group(0)
        return re.sub(r'alt="([^"]+)"', repl_alt, linha)

    # Caso 2: Linha de legenda de tabela Markdown: | **001**<br>Nome |
    if linha.strip().startswith('|') and '<br>' in linha:
        celulas = linha.split('|')
        novas_celulas = []
        for c in celulas:
            if '<br>' in c:
                partes = c.split('<br>', 1)
                texto_pos = partes[1].strip()
                if CHINESE_REGEX.search(texto_pos):
                    novas_celulas.append(f'{partes[0]}<br>{traduzir_trecho_api(texto_pos)} ')
                else:
                    novas_celulas.append(c)
            elif CHINESE_REGEX.search(c):
                novas_celulas.append(f' {traduzir_trecho_api(c.strip())} ')
            else:
                novas_celulas.append(c)
        return '|'.join(novas_celulas)

    # Caso 3: Linhas gerais de Markdown (títulos, parágrafos, listas, links)
    placeholders = []

    # Proteger tags HTML puras como <a href="..."> ou <kbd> ou <a id="...">
    def repl_tag(m):
        tag = m.group(0)
        # Se for tag que tem texto visível como <kbd>texto</kbd>, tratar fora
        idx = len(placeholders)
        placeholders.append(tag)
        return f'___HTML_TAG_{idx}___'

    # Proteger tags HTML fechadas e vazias (ex: <a href="..."></a> ou âncoras <a id="..."></a>)
    linha_mod = re.sub(r'<a\s+[^>]*>.*?</a>', repl_tag, linha)
    linha_mod = re.sub(r'<[^>]+>', repl_tag, linha_mod)

    # Proteger links markdown normais [texto](url) -> guardar url intacta
    def repl_md_link(m):
        txt = m.group(1)
        url = m.group(2)
        idx = len(placeholders)
        placeholders.append(url)
        return f'[{txt}](___ATTR_{idx}___)'

    linha_mod = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', repl_md_link, linha_mod)

    # Proteger código inline `...`
    def repl_inline_code(m):
        code = m.group(1)
        idx = len(placeholders)
        placeholders.append(code)
        return f'`___ATTR_{idx}___`'

    linha_mod = re.sub(r'`([^`]+)`', repl_inline_code, linha_mod)

    # Traduz o texto da linha
    linha_traduzida = traduzir_trecho_api(linha_mod)

    # Restaura todos os placeholders
    for idx, val in enumerate(placeholders):
        padrao_attr = re.compile(rf'___\s*ATTR_{idx}\s*___', re.IGNORECASE)
        linha_traduzida = padrao_attr.sub(val, linha_traduzida)
        padrao_html = re.compile(rf'___\s*HTML_TAG_{idx}\s*___', re.IGNORECASE)
        linha_traduzida = padrao_html.sub(val, linha_traduzida)

    return linha_traduzida

def traduzir_documento(caminho_arquivo):
    """Lê o arquivo, preserva blocos de código e traduz o conteúdo em chinês."""
    with open(caminho_arquivo, 'r', encoding='utf-8') as f:
        linhas = f.readlines()

    linhas_traduzidas = []
    em_bloco_codigo = False

    for linha in linhas:
        strip_l = linha.strip()
        if strip_l.startswith('```'):
            em_bloco_codigo = not em_bloco_codigo
            linhas_traduzidas.append(linha)
            continue

        if em_bloco_codigo:
            linhas_traduzidas.append(linha)
        else:
            linhas_traduzidas.append(traduzir_linha_markdown(linha))

    conteudo_final = ''.join(linhas_traduzidas)
    with open(caminho_arquivo, 'w', encoding='utf-8') as f:
        f.write(conteudo_final)

def traduzir_projeto(diretorio_raiz):
    """Varre o projeto e traduz apenas documentos de texto que contenham chinês."""
    caminho_script = os.path.abspath(__file__)
    arquivos_alvo = []

    for raiz, _, arquivos in os.walk(diretorio_raiz):
        if '.git' in raiz or 'scripts' in raiz or 'dist' in raiz:
            continue

        for arquivo in arquivos:
            extensao = os.path.splitext(arquivo)[1].lower()
            if extensao in EXTENSOES_PERMITIDAS:
                caminho_completo = os.path.abspath(os.path.join(raiz, arquivo))
                if caminho_completo == caminho_script:
                    continue

                try:
                    with open(caminho_completo, 'r', encoding='utf-8') as f:
                        conteudo = f.read()
                    if CHINESE_REGEX.search(conteudo):
                        arquivos_alvo.append(caminho_completo)
                except Exception as e:
                    print(f"Erro ao analisar {arquivo}: {e}", flush=True)

    print(f"Encontrados {len(arquivos_alvo)} documentos de texto em chinês para traduzir:\n", flush=True)
    for idx, caminho in enumerate(arquivos_alvo, 1):
        rel = os.path.relpath(caminho, diretorio_raiz)
        print(f"[{idx}/{len(arquivos_alvo)}] Traduzindo: {rel}", flush=True)
        traduzir_documento(caminho)
        print(f"  ✓ Concluído: {rel}", flush=True)

    print("\nTodos os documentos de texto em chinês foram traduzidos com sucesso!", flush=True)

if __name__ == "__main__":
    pasta_projeto = os.path.dirname(os.path.abspath(__file__))
    traduzir_projeto(pasta_projeto)
