"""Isolated integration checks; creates a temporary project, never edits your store.
Run: python admin_update/check_update.py
"""
import importlib.util
from io import BytesIO
from pathlib import Path
import sys
import tempfile
from PIL import Image

BUNDLE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('installer', BUNDLE / 'install_update.py')
installer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(installer)

with tempfile.TemporaryDirectory() as directory:
    root = Path(directory)
    originals = {
        'run.py': 'from app import create_app\napp = create_app()\n',
        'app/__init__.py': '''products = {"P101":{"name":"Wireless Mouse","category":"Electronics","price_paise":79900,"stock":20}}''',
        'app/templates/catalog.html': '''<!doctype html><html><body>
        <nav class="category-nav"><button>Electronics</button></nav>
<div class="product-grid">{% for product_id, product in products.items() %}old{% endfor %}</div>
<a href="#contact">Contact us</a></body></html>''',
        'app/static/css/style.css': '/* existing focus fix */',
        'app/static/js/home.js': '''// ---------- Search and category filters ----------
oldFilter();
// ---------- Banner carousel ----------
// existing carousel remains
''',
    }
    for name, content in originals.items():
        target = root / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding='utf-8')
    installer.install(root, BUNDLE)
    assert 'existing focus fix' in (root / 'app/static/css/style.css').read_text()
    assert 'existing carousel remains' in (root / 'app/static/js/home.js').read_text()
    try:
        installer.prepare(root, BUNDLE)
        raise AssertionError('Installer allowed duplicate update')
    except ValueError:
        pass
    sys.path.insert(0, str(root))
    from app import create_app
    from app.database import get_db
    config = dict(TESTING=True, SECRET_KEY='isolated-test-key', DATABASE=str(root/'test.db'))
    app = create_app(config)
    client = app.test_client()
    assert client.get('/').status_code == 200
    assert b'Wireless Mouse' in client.get('/').data
    assert client.get('/admin/').status_code == 302
    assert b'not configured' not in client.get('/admin/login').data  # setup instructions instead
    assert b'set-admin-password' in client.get('/admin/login').data
    runner = app.test_cli_runner()
    result = runner.invoke(args=['set-admin-password'], input='a-long-test-password\na-long-test-password\n')
    assert result.exit_code == 0, result.output

    def token():
        client.get('/admin/login')
        with client.session_transaction() as session:
            return session['csrf']

    assert client.post('/admin/login', data={'password':'a-long-test-password'}).status_code == 400
    assert client.post('/admin/login', data={'password':'wrong', 'csrf_token':token()}).status_code == 401
    assert client.post('/admin/login', data={'password':'a-long-test-password', 'csrf_token':token()}).status_code == 302
    assert client.get('/admin/').status_code == 200

    def photo():
        out = BytesIO()
        Image.new('RGB',(40,40),'green').save(out, 'PNG')
        out.seek(0)
        return out

    def post_product(**changes):
        values = dict(name='New headphones', category=' electronics ', subcategory=' Audio ', price='799.50', stock='4')
        values.update(changes)
        image = values.pop('image', None)
        values['csrf_token'] = token()
        values['image'] = (image if image is not None else photo(), 'product.png')
        return client.post('/admin/products', data=values, content_type='multipart/form-data')

    assert post_product().status_code == 302
    with app.app_context():
        db = get_db()
        assert db.execute('SELECT COUNT(*) FROM categories').fetchone()[0] == 1
        product = dict(db.execute("SELECT * FROM products WHERE name='New headphones'").fetchone())
        assert product['price_paise'] == 79950 and product['stock'] == 4
        assert (Path(app.static_folder)/product['image_path']).is_file()
        category = product['category_id']
        subcategory = product['subcategory_id']
    assert b'New headphones' in client.get('/').data
    assert client.get('/api/catalog',query_string={'category':category,'subcategory':subcategory}).json['count'] == 1
    assert client.get('/api/catalog',query_string={'q':'HEADPHONES'}).json['count'] == 1
    assert client.get('/api/catalog',query_string={'category':'999999'}).json['count'] == 0
    assert client.get('/api/catalog?category=invalid').status_code == 400
    # Unicode/case/whitespace normalization and subcategory reuse.
    assert post_product(name='Second item', category='ELECTRONICS', subcategory='audio', stock='0', price='0').status_code == 302
    with app.app_context():
        assert get_db().execute('SELECT COUNT(*) FROM subcategories').fetchone()[0] == 1
    # Same subcategory name is allowed under a DIFFERENT parent category.
    assert post_product(name='Third item', category='Clothing', subcategory='Audio').status_code == 302
    with app.app_context():
        assert get_db().execute('SELECT COUNT(*) FROM subcategories').fetchone()[0] == 2
    # Failures cannot create categories or products, or leave image files behind.
    before_files = set(Path(app.config['UPLOAD_FOLDER']).iterdir())
    for change in [dict(stock='-1'),dict(stock='1.5'),dict(price='NaN'),dict(price='Infinity'),dict(price='1.234'),
                   dict(name=' '),dict(image=BytesIO(b'not an image'))]:
        assert post_product(category='Should not exist', **change).status_code == 400, change
    assert set(Path(app.config['UPLOAD_FOLDER']).iterdir()) == before_files
    with app.app_context():
        assert get_db().execute("SELECT COUNT(*) FROM categories WHERE name='Should not exist'").fetchone()[0] == 0
        assert get_db().execute('SELECT COUNT(*) FROM products').fetchone()[0] == 4
    assert post_product(name='<script>alert(1)</script>').status_code == 302
    html = client.get('/').data
    assert b'<script>alert(1)</script>' not in html and b'&lt;script&gt;' in html
    response = client.post('/admin/taxonomy',data={'category':'Books','subcategory':'Fiction','csrf_token':token()})
    assert response.status_code == 302 and b'Books' in client.get('/').data
    assert client.get('/api/catalog').json['count'] == 5
    # Verify persistence and no reseeding after a complete Flask app restart.
    restarted = create_app(config).test_client()
    assert restarted.get('/api/catalog').json['count'] == 5
    assert b'New headphones' in restarted.get('/').data
    # Real upload bytes are served correctly from their saved URL.
    assert client.get('/static/' + product['image_path']).status_code == 200
    assert client.post('/admin/logout',data={'csrf_token':token()}).status_code == 302
    assert client.get('/admin/').status_code == 302
    print('PASS: installer/backup, login/CSRF, product/image save, category reuse, parent-scoped subcategories, filtering, validation, escaping, persistence and logout.')
