import re
import codecs

path = r'c:\Automação e Inteligência Financeira Daniel\js\main.js'
with codecs.open(path, 'r', 'utf-8') as f:
    content = f.read()

new_funcs = '''
function getSelectedTicker() {
    const sel = document.getElementById('ticker-selector');
    return sel ? sel.value : 'ITUB4';
}
function getSelectedTickerClean() {
    return getSelectedTicker().replace('.SA', '');
}
'''
if 'getSelectedTicker' not in content:
    content = new_funcs + '\n' + content

content = content.replace("'itub4_sentimento.json?t='", "getSelectedTickerClean() + '_sentimento.json?t='")
content = content.replace("'itub4_processado_final.csv?t='", "getSelectedTickerClean() + '_processado_final.csv?t='")
content = content.replace("'itub4_previsoes_finais.csv?t='", "getSelectedTickerClean() + '_previsoes_finais.csv?t='")
content = content.replace("'itub4_metricas.json?t='", "getSelectedTickerClean() + '_metricas.json?t='")

# Replace fetch body in sentiment
content = content.replace(
    "const body = JSON.stringify({ start: startDate, end: endDate });",
    "const body = JSON.stringify({ start: startDate, end: endDate, ticker: getSelectedTicker() });"
)
content = content.replace(
    "const body = JSON.stringify({ start, end });",
    "const body = JSON.stringify({ start, end, ticker: getSelectedTicker() });"
)

# In `/retrain` function (which uses 'start' and 'end' inputs)
# Wait, let's find how `/retrain` is called. It probably reads `document.getElementById('train-start').value`
# Let's replace: JSON.stringify({ start: start, end: end }) or similar
content = re.sub(
    r"body:\s*JSON\.stringify\(\{\s*start:\s*start\s*,\s*end:\s*end\s*\}\)",
    "body: JSON.stringify({ start: start, end: end, ticker: getSelectedTicker() })",
    content
)

# Replace 'ITUB4' mentions in UI strings inside js
content = content.replace("Preço Real (ITUB4)", "Preço Real")
content = content.replace("ITUB4 com as projeções", "a ação com as projeções")
content = content.replace("da ITUB4. Isso", "da ação. Isso")

# Add event listener for ticker selector
if 'ticker-selector' not in content and 'setupCollapsiblePanels();' in content:
    content = content.replace(
        "setupCollapsiblePanels();",
        """setupCollapsiblePanels();
    const sel = document.getElementById('ticker-selector');
    if (sel) {
        sel.addEventListener('change', () => {
            const t = sel.value;
            const tClean = getSelectedTickerClean();
            const text = sel.options[sel.selectedIndex].text;
            if(document.getElementById('logo-ticker')) document.getElementById('logo-ticker').innerText = t;
            if(document.getElementById('db-ticker-name')) document.getElementById('db-ticker-name').innerText = t;
            if(document.getElementById('price-ticker-name')) document.getElementById('price-ticker-name').innerText = text;
            
            // clear charts and re-fetch
            const btn = document.getElementById('btn-refresh');
            if(btn) btn.click();
        });
        // trigger once to set initial text
        sel.dispatchEvent(new Event('change'));
    }
"""
    )

with codecs.open(path, 'w', 'utf-8') as f:
    f.write(content)
print('Done patching js!')
