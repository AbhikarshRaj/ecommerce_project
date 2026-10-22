"""Install this milestone over the homepage from our tutorial, with backups.
Run from ecommerce_project: python admin_update/install_update.py
"""
import ast
from datetime import datetime
import json
from pathlib import Path
import shutil
import sys

MARKER = '<!-- ADMIN CATALOG UPDATE v1 -->'


def prepare(root, bundle):
    template_path = root / 'app/templates/catalog.html'
    js_path = root / 'app/static/js/home.js'
    init_path = root / 'app/__init__.py'
    for path in [root / 'run.py', template_path, js_path, init_path, root / 'app/static/css/style.css']:
        if not path.is_file():
            raise ValueError(f'Missing file: {path}. Place admin_update inside ecommerce_project.')
    html = template_path.read_text(encoding='utf-8-sig')
    js = js_path.read_text(encoding='utf-8-sig')
    if MARKER in html:
        raise ValueError('This update is already installed. No files were changed.')
    # All checks and transformations happen before writing anything.
    start = html.index('        <nav class="category-nav"')
    stop = html.index('</nav>', start) + len('</nav>')
    navigation = '''        <nav class="category-nav" aria-label="Product categories">
            <div class="container category-list">
                <button class="category-button active" data-category="all" aria-pressed="true">All products</button>
                {% for category in categories %}
                <button class="category-button" data-category="{{ category.id }}" aria-pressed="false">{{ category.name }}</button>
                {% endfor %}
            </div>
        </nav>'''
    html = html[:start] + navigation + html[stop:]
    start = html.index('{% for product_id, product in products.items() %}')
    stop = html.index('{% endfor %}', start) + len('{% endfor %}')
    html = html[:start] + "{% include '_product_cards.html' %}" + html[stop:]
    anchor = '<div class="product-grid">'
    if html.count(anchor) != 1:
        raise ValueError('Could not identify product grid. No files changed.')
    html = html.replace(anchor, '''<div class="subcategory-toolbar">
                    <label for="subcategory-filter">Subcategory</label>
                    <select id="subcategory-filter"><option value="">All subcategories</option></select>
                </div>
                ''' + anchor)
    footer = '<a href="#contact">Contact us</a>'
    if footer not in html:
        raise ValueError('Could not identify footer link. No files changed.')
    html = html.replace(footer, footer + '\n                <a href="{{ url_for(\'admin.dashboard\') }}">Admin</a>', 1)
    data = '''<script type="application/json" id="store-taxonomy-data">{{ {'categories':categories,'subcategories':subcategories}|tojson }}</script>'''
    html = html.replace('</body>', MARKER + '\n' + data + '\n</body>')
    start = js.index('// ---------- Search and category filters ----------')
    stop = js.index('// ---------- Banner carousel ----------', start)
    js = js[:start] + (bundle / 'search_block.js').read_text(encoding='utf-8') + js[stop:]
    # Safely extract the old data; never execute the original Python file.
    tree = ast.parse(init_path.read_text(encoding='utf-8-sig'))
    seed = None
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == 'products' for t in node.targets):
            try:
                candidate = ast.literal_eval(node.value)
            except (ValueError, TypeError):
                continue
            if isinstance(candidate, dict):
                seed = candidate
                break
    if seed is None:
        raise ValueError('Could not extract your original product dictionary. No files changed; ask for help adapting the update.')
    for pid, p in seed.items():
        if not isinstance(pid, str) or not isinstance(p, dict) or not all(k in p for k in ('name','category','price_paise','stock')):
            raise ValueError('Original products have an unexpected format. No files changed.')
        if not isinstance(p['name'],str) or not p['name'].strip() or not isinstance(p['category'],str) or not p['category'].strip():
            raise ValueError('Product names and categories must not be empty.')
        if type(p['price_paise']) is not int or p['price_paise'] < 0 or type(p['stock']) is not int or p['stock'] < 0:
            raise ValueError('Original prices and stock must be non-negative integers.')
    css = (root / 'app/static/css/style.css').read_text(encoding='utf-8-sig')
    css += '''\n/* Admin catalog integration */
.subcategory-toolbar{display:flex;align-items:center;gap:12px;margin:0 0 22px;font-size:13px;flex-wrap:wrap}
.subcategory-toolbar select{max-width:100%;padding:9px 12px;border:1px solid var(--border);border-radius:8px;background:white;color:var(--ink);font:inherit}
.subcategory-toolbar select:focus-visible{outline:2px solid var(--green);outline-offset:3px}
.product-grid[aria-busy="true"]{opacity:.6}
'''
    writes = {
        Path('app/templates/catalog.html'): html.encode('utf-8'),
        Path('app/static/js/home.js'): js.encode('utf-8'),
        Path('app/static/css/style.css'): css.encode('utf-8'),
        Path('app/seed_products.json'): json.dumps(seed,ensure_ascii=False,indent=2).encode('utf-8'),
    }
    for source in (bundle / 'payload').rglob('*'):
        if source.is_file() and '__pycache__' not in source.parts and source.suffix != '.pyc':
            writes[source.relative_to(bundle / 'payload')] = source.read_bytes()
    return writes


def install(root, bundle):
    writes = prepare(root, bundle)
    backup = root / ('backup_before_admin_' + datetime.now().strftime('%Y%m%d_%H%M%S_%f'))
    backup.mkdir()
    originals = {}
    for relative in writes:
        target = root / relative
        originals[relative] = target.read_bytes() if target.exists() else None
        if target.exists():
            destination = backup / relative
            destination.parent.mkdir(parents=True,exist_ok=True)
            shutil.copy2(target, destination)
    try:
        for relative, content in writes.items():
            target = root / relative
            target.parent.mkdir(parents=True,exist_ok=True)
            target.write_bytes(content)
    except Exception:
        for relative, content in originals.items():
            target = root / relative
            if content is None:
                target.unlink(missing_ok=True)
            else:
                target.write_bytes(content)
        raise
    print(f'Installed {len(writes)} files. Original files backed up in {backup.name}')
    print('Next: python -m pip install -r admin_update/requirements-admin.txt')
    print('Then: python -m flask --app run set-admin-password')
    print('Then: python run.py')


if __name__ == '__main__':
    bundle = Path(__file__).resolve().parent
    try:
        install(bundle.parent, bundle)
    except (ValueError, OSError, SyntaxError) as error:
        print(f'Update stopped: {error}')
        sys.exit(1)
