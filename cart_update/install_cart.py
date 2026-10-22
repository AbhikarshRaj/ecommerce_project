"""Apply the cart milestone to the installed admin catalog update."""
from datetime import datetime
from pathlib import Path
import re
import shutil
import sys

MARKER = '<!-- CART UPDATE v1 -->'


def once(text, old, new, description):
    if text.count(old) != 1:
        raise ValueError(f'Could not uniquely locate {description}. No files were changed.')
    return text.replace(old, new, 1)


def prepare(root, bundle):
    paths = ['app/__init__.py','app/admin.py','app/templates/catalog.html',
             'app/templates/_product_cards.html','app/static/js/home.js']
    text = {}
    for name in paths:
        path = root / name
        if not path.is_file():
            raise ValueError(f'Missing {name}. Install the admin catalog update first.')
        text[name] = path.read_text(encoding='utf-8-sig')
    html = text['app/templates/catalog.html']
    if MARKER in html:
        raise ValueError('The cart update is already installed. No files were changed.')
    if '<!-- ADMIN CATALOG UPDATE v1 -->' not in html:
        raise ValueError('This installer expects the earlier admin catalog update. No files changed.')
    text['app/__init__.py'] = once(text['app/__init__.py'], '    register_commands(app)\n',
        '    register_commands(app)\n    from .cart import init_cart\n    init_cart(app)\n', 'application registration')
    # Admin sign-in/out must not throw away the customer's cart identity.
    admin_source = text['app/admin.py']
    if admin_source.count('session.clear()') != 2:
        raise ValueError('Admin session code differs from the expected version. No files changed.')
    def preserve(match):
        indent = match.group(1)
        return '\n'.join(indent + line for line in [
            "saved_cart_id = session.get('cart_id')", 'session.clear()',
            'if saved_cart_id:', "    session['cart_id'] = saved_cart_id", '    session.permanent = True'])
    text['app/admin.py'] = re.sub(r'(?m)^([ \t]*)session\.clear\(\)', preserve, admin_source)
    extra = '''    <!-- CART UPDATE v1 -->
    <link rel="stylesheet" href="{{ url_for('static', filename='css/cart.css') }}">
    <script defer src="{{ url_for('static', filename='js/cart.js') }}"></script>
'''
    text['app/templates/catalog.html'] = once(html, '</head>', extra + '</head>', 'homepage head')
    cards = text['app/templates/_product_cards.html']
    text['app/templates/_product_cards.html'] = once(cards, '  </div>\n</article>',
        "    {% include '_cart_controls.html' %}\n  </div>\n</article>", 'product card footer')
    js = text['app/static/js/home.js']
    start = js.index('// ---------- Cart placeholder ----------')
    stop = js.index('// ---------- Footer ----------', start)
    text['app/static/js/home.js'] = js[:start] + '// Cart interactions are now handled by cart.js.\n\n' + js[stop:]
    writes = {Path(name):content.encode('utf-8') for name,content in text.items()}
    for path in (bundle/'payload').rglob('*'):
        if path.is_file() and '__pycache__' not in path.parts and path.suffix != '.pyc':
            relative = path.relative_to(bundle/'payload')
            if (root/relative).exists():
                raise ValueError(f'{relative} already exists. Stop to avoid overwriting other cart work.')
            writes[relative] = path.read_bytes()
    return writes


def install(root,bundle):
    writes = prepare(root,bundle)
    backup = root/('backup_before_cart_'+datetime.now().strftime('%Y%m%d_%H%M%S_%f'))
    backup.mkdir()
    originals = {}
    for relative in writes:
        target = root/relative
        originals[relative] = target.read_bytes() if target.exists() else None
        if target.exists():
            copy = backup/relative
            copy.parent.mkdir(parents=True,exist_ok=True)
            shutil.copy2(target,copy)
    try:
        for relative,content in writes.items():
            target = root/relative
            target.parent.mkdir(parents=True,exist_ok=True)
            target.write_bytes(content)
    except Exception:
        for relative,content in originals.items():
            target=root/relative
            if content is None:
                target.unlink(missing_ok=True)
            else:
                target.write_bytes(content)
        raise
    print(f'Cart installed. Backup: {backup.name}')
    print('Run python run.py and hard-refresh your browser with Ctrl+F5.')
    print('Cart page: http://127.0.0.1:5000/cart')


if __name__=='__main__':
    bundle=Path(__file__).resolve().parent
    try:
        install(bundle.parent,bundle)
    except (ValueError,OSError) as error:
        print(f'Update stopped: {error}')
        sys.exit(1)
