"""Run against an ISOLATED temporary copy of the installed application.
Usage: python cart_update/check_cart.py
Never modifies the real database or uploads.
"""
import json
from pathlib import Path
import shutil
import sys
import tempfile

source = Path(sys.argv[1]).resolve() if len(sys.argv)>1 else Path(__file__).resolve().parent.parent
if not (source/'app/cart.py').exists():
    raise SystemExit('Install the cart update first, then run this check.')
with tempfile.TemporaryDirectory() as directory:
    root=Path(directory)
    shutil.copytree(source/'app',root/'app',ignore=shutil.ignore_patterns('__pycache__','*.pyc','uploads','images'))
    seed={
        'P101':dict(name='Test mouse',category='Electronics',price_paise=79950,stock=3),
        'P102':dict(name='Test shirt',category='Clothing',price_paise=50000,stock=0),
        'P103':dict(name='Test pen',category='Stationery',price_paise=1500,stock=1000),
    }
    (root/'app/seed_products.json').write_text(json.dumps(seed))
    sys.path.insert(0,str(root))
    from app import create_app
    from app.database import get_db
    from app.bounded_stack import BoundedStack
    stack=BoundedStack(capacity=3)
    for value in range(5): stack.push(value)
    assert stack.items()==[2,3,4]
    assert stack.pop()==4 and stack.pop()==3
    stack.push(5)
    assert stack.items()==[2,5]
    assert stack.pop()==5 and stack.pop()==2
    try:
        stack.pop()
        raise AssertionError('Empty stack should fail')
    except IndexError:
        pass
    config=dict(TESTING=True,SECRET_KEY='cart-test-key',DATABASE=str(root/'test.db'))
    app=create_app(config)
    client=app.test_client()
    def state(client=client):
        response=client.get('/api/cart')
        assert response.status_code==200
        return response.json
    def action(kind,pid='P101',quantity='',expected_status=200,version=None,client=client,**extra):
        current=state(client)
        data=dict(action=kind,product_id=pid,quantity=str(quantity),csrf_token=current['csrf_token'],version=str(current['version'] if version is None else version))
        data.update(extra)
        response=client.post('/api/cart/action',data=data)
        assert response.status_code==expected_status,(response.status_code,response.data)
        return response.json
    assert client.get('/cart').status_code==200
    assert state()['count']==0
    assert client.post('/api/cart/action',data={'action':'add'}).status_code==400
    assert action('add')['count']==1
    assert state()['subtotal_paise']==79950
    assert action('increment')['count']==2
    assert action('increment')['count']==3
    assert action('increment',expected_status=409)['count']==3
    assert action('decrement')['count']==2
    assert action('set',quantity=1,price_paise='1')['subtotal_paise']==79950
    assert action('decrement')['count']==0
    assert action('undo')['count']==1
    assert action('redo')['count']==0
    assert action('undo')['count']==1
    assert action('increment')['count']==2
    assert not state()['can_redo']
    assert action('redo',expected_status=400)['count']==2
    assert action('remove')['count']==0
    assert action('undo')['count']==2
    assert action('add',pid='P103')['count']==3
    assert action('clear')['count']==0
    assert action('undo')['count']==3
    assert action('redo')['count']==0
    assert action('add',pid='P102',expected_status=409)['count']==0
    assert action('add',pid='missing',expected_status=404)['count']==0
    for quantity in ('-1','1.5','NaN','1000'):
        assert action('set',quantity=quantity,expected_status=400)['count']==0
    assert action('set',pid='P103',quantity=999)['count']==999
    assert action('increment',pid='P103',expected_status=400)['count']==999
    assert action('clear')['count']==0
    assert action('add')['count']==1
    # Separate browser has its own cart.
    second=app.test_client()
    assert state(second)['count']==0
    assert action('add',pid='P103',client=second)['count']==1
    assert state()['items'][0]['id']=='P101'
    # Same session in another tab: stale revision is rejected, not overwritten.
    stale=state()['version']
    assert action('increment')['count']==2
    assert action('increment',version=stale,expected_status=409)['count']==2
    # Undo restoration is rejected if stock has fallen; history remains untouched.
    assert action('remove')['count']==0
    old=state()
    with app.app_context():
        db=get_db()
        with db: db.execute("UPDATE products SET stock=1 WHERE id='P101'")
    assert action('undo',expected_status=409)['count']==0
    assert state()['version']==old['version'] and state()['can_undo']
    with app.app_context():
        db=get_db()
        with db: db.execute("UPDATE products SET stock=3 WHERE id='P101'")
    assert action('undo')['count']==2
    # Current prices are read from SQLite, not from the browser or old history.
    with app.app_context():
        db=get_db()
        with db: db.execute("UPDATE products SET price_paise=80000 WHERE id='P101'")
    assert state()['subtotal_paise']==160000
    # Both cart and stacks survive recreation of the Flask app with the same cookie.
    restarted=create_app(config).test_client()
    cookie=client.get_cookie('session')
    restarted.set_cookie('session',cookie.value)
    assert state(restarted)['count']==2
    assert action('undo',client=restarted)['count']==1
    assert action('redo',client=restarted)['count']==2
    # Admin login/logout must preserve the customer cart.
    cli=app.test_cli_runner()
    result=cli.invoke(args=['set-admin-password'],input='long-test-password\nlong-test-password\n')
    assert result.exit_code==0,result.output
    before=state()['count']
    response=client.post('/admin/login',data={'password':'long-test-password','csrf_token':state()['csrf_token']})
    assert response.status_code==302
    assert state()['count']==before
    assert client.post('/admin/logout',data={'csrf_token':state()['csrf_token']}).status_code==302
    assert state()['count']==before
    assert b'data-cart-action="add"' in client.get('/api/catalog').json['html'].encode()
    # Retention stays bounded under continuous interaction.
    for index in range(105):
        action('set',pid='P103',quantity=1 if index%2==0 else 2)
    assert len(state()['history'])==100
    print('PASS: bounded-stack wraparound, quantity controls, totals, live stock/prices, removal/clear, undo/redo, CSRF, isolation, stale revisions, restart persistence, admin session preservation and 100-action retention.')
