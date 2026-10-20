import pytest, sqlite3, hashlib
from sprout import create_app, connect
from werkzeug.security import generate_password_hash

@pytest.fixture
def app(tmp_path): return create_app({'TESTING':True,'DATABASE':str(tmp_path/'test.sqlite')})
@pytest.fixture
def c(app): return app.test_client()
def token(c): return c.get('/api/session').json['csrf']
def write(c,path,data,method='post',csrf=None): return getattr(c,method)(path,json=data,headers={'X-CSRF-Token':csrf or token(c)})
def register(c,email='demo@example.test',name='Demo User'): return write(c,'/api/register',{'name':name,'email':email,'password':'Sample-pass-2026'})
def cart(c,items=None): return write(c,'/api/cart',{'items':items if items is not None else [{'product_id':1,'quantity':2}]},'put')
def order(c,key='abcdefgh12345678'): return write(c,'/api/orders',{'address':'123 Example Street, Demo City','request_key':key})
def admin(c,app):
    with connect(app.config['DATABASE']) as db: db.execute('INSERT INTO users(name,email,password_hash,role) VALUES(?,?,?,?)',('Admin Demo','admin@example.test',generate_password_hash('Admin-demo-2026'),'admin'))
    return write(c,'/api/login',{'email':'admin@example.test','password':'Admin-demo-2026'})

def test_home_and_security_headers(c):
    r=c.get('/'); assert r.status_code==200; assert b'sprout' in r.data
    assert "script-src 'self'" in r.headers['Content-Security-Policy']; assert r.headers['X-Content-Type-Options']=='nosniff'
def test_cookie_flags(c):
    r=c.get('/api/session'); assert 'HttpOnly' in r.headers['Set-Cookie']; assert 'SameSite=Strict' in r.headers['Set-Cookie']
def test_csrf_required(c): assert c.post('/api/register',json={}).status_code==403
def test_origin_blocked(c): assert c.post('/api/logout',json={},headers={'X-CSRF-Token':token(c),'Origin':'https://evil.example'}).status_code==403
def test_catalog_seed_and_filters(c):
    assert len(c.get('/api/products').json['products'])==20
    assert len(c.get('/api/products?q=MILK').json['products'])==1
    assert len(c.get('/api/products?category=Bakery').json['products'])==2
    assert c.get('/api/products?q=nonexistent').json['products']==[]
def test_register_hash_and_customer_role(c,app):
    r=register(c); assert r.status_code==200; assert r.json['user']['role']=='customer'
    with connect(app.config['DATABASE']) as db:
        h=db.execute('SELECT password_hash FROM users').fetchone()[0]; assert h.startswith('scrypt:'); assert 'Sample-pass' not in h
@pytest.mark.parametrize('d',[{}, {'name':'X','email':'a','password':'short'}, {'name':3,'email':[], 'password':4}, {'name':'Demo','email':'a@b.test','password':'a'*129}])
def test_bad_registration(c,d): assert write(c,'/api/register',d).status_code==400
def test_duplicate_email(c): register(c); assert register(c).status_code==409
def test_role_injection(c):
    r=write(c,'/api/register',{'name':'Demo','email':'x@y.test','password':'Sample-pass-2026','role':'admin'}); assert r.json['user']['role']=='customer'
def test_login_logout_rotation(c):
    old=token(c); register(c); assert write(c,'/api/logout',{}).status_code==200
    assert c.get('/api/orders').status_code==401
    assert write(c,'/api/login',{'email':'demo@example.test','password':'wrong'}).status_code==401
    r=write(c,'/api/login',{'email':'demo@example.test','password':'Sample-pass-2026'}); assert r.status_code==200; assert r.json['csrf']!=old
    assert write(c,'/api/logout',{},csrf=old).status_code==403
def test_session_expiry(c,app):
    register(c)
    with connect(app.config['DATABASE']) as db: db.execute('UPDATE sessions SET expires=0')
    assert c.get('/api/orders').status_code==401
def test_cart_auth(c): assert c.get('/api/cart').status_code==401; assert cart(c).status_code==401
@pytest.mark.parametrize('items',[[{'product_id':1,'quantity':-1}],[{'product_id':1,'quantity':True}],[{'product_id':1,'quantity':21}],[{'product_id':1,'quantity':1},{'product_id':1,'quantity':2}],{},[{}]])
def test_invalid_cart(c,items): register(c); assert cart(c,items).status_code==400
def test_missing_product(c): register(c); assert cart(c,[{'product_id':999,'quantity':1}]).status_code==404
def test_cart_persistence(c):
    register(c); cart(c); write(c,'/api/logout',{}); write(c,'/api/login',{'email':'demo@example.test','password':'Sample-pass-2026'}); assert c.get('/api/cart').json['items']==[{'product_id':1,'quantity':2}]
def test_empty_order(c): register(c); assert order(c).status_code==400
def test_server_pricing_stock_and_replay(c,app):
    register(c);cart(c);r=order(c);assert r.status_code==201;assert r.json['total']==9800
    assert c.get('/api/cart').json['items']==[]
    replay=order(c);assert replay.json['id']==r.json['id'];assert replay.json['replayed']
    with connect(app.config['DATABASE']) as db: assert db.execute('SELECT stock FROM products WHERE id=1').fetchone()[0]==46;assert db.execute('SELECT count(*) FROM orders').fetchone()[0]==1
    history=c.get('/api/orders').json['orders'];assert history[0]['total']==9800;assert history[0]['items'][0]['price']==4900

def test_price_tampering_ignored(c):
    register(c); cart(c);r=write(c,'/api/orders',{'address':'123 Fake Street','request_key':'abcdefgh12345678','total':1,'price':1});assert r.json['total']==9800
def test_insufficient_stock_rolls_back(c,app):
    register(c);cart(c)
    with connect(app.config['DATABASE']) as db: db.execute('UPDATE products SET stock=1 WHERE id=1')
    assert order(c).status_code==409;assert c.get('/api/cart').json['items'][0]['quantity']==2
    with connect(app.config['DATABASE']) as db: assert db.execute('SELECT count(*) FROM orders').fetchone()[0]==0
@pytest.mark.parametrize('payload',[{'address':'short','request_key':'abcdefgh12345678'},{'address':'123 Fake Street','request_key':'bad'},{'address':[],'request_key':True}])
def test_invalid_checkout(c,payload): register(c);cart(c);assert write(c,'/api/orders',payload).status_code==400

def test_user_isolation(c,app):
    register(c);cart(c);order(c)
    other=app.test_client();register(other,'other@example.test');assert other.get('/api/orders').json['orders']==[];assert other.get('/api/cart').json['items']==[]
def test_admin_protection(c):
    assert c.get('/api/admin').status_code==401
    register(c);assert c.get('/api/admin').status_code==403
    assert write(c,'/api/admin/products/1',{'price':1,'stock':0},'patch').status_code==403

def test_admin_updates_and_order_snapshot(c,app):
    register(c);cart(c);order(c);admin(c,app)
    assert c.get('/api/admin').status_code==200
    assert write(c,'/api/admin/products/1',{'price':5000,'stock':8},'patch').status_code==200
    assert c.get('/api/products?q=bananas').json['products'][0]['price']==5000
    assert c.get('/api/admin').json['orders'][0]['items'][0]['price']==4900
    assert write(c,'/api/admin/orders/1',{'status':'Demo completed'},'patch').status_code==400
    assert write(c,'/api/admin/orders/1',{'status':'Demo packed'},'patch').status_code==200
    assert write(c,'/api/admin/orders/1',{'status':'Demo completed'},'patch').status_code==200
@pytest.mark.parametrize('d',[{'price':-1,'stock':1},{'price':1.5,'stock':2},{'price':1,'stock':-1},{'price':True,'stock':1}])
def test_admin_validation(c,app,d): admin(c,app);assert write(c,'/api/admin/products/1',d,'patch').status_code==400

def test_sql_injection_is_data(c):
    assert c.get('/api/products?q=%27%20OR%201%3D1--').json['products']==[]
    assert write(c,'/api/login',{'email':"' OR 1=1--",'password':'Whatever-2026'}).status_code==401

def test_rate_limit(c):
    for _ in range(20): assert write(c,'/api/login',{}).status_code==401
    assert write(c,'/api/login',{}).status_code==429

def test_large_body(c): assert c.post('/api/register',data='a'*40000,headers={'Content-Type':'application/json','X-CSRF-Token':token(c)}).status_code==413

def test_persistence_reopen(c,app):
    register(c);cart(c);order(c)
    app2=create_app({'TESTING':True,'DATABASE':app.config['DATABASE']});other=app2.test_client();write(other,'/api/login',{'email':'demo@example.test','password':'Sample-pass-2026'});assert len(other.get('/api/orders').json['orders'])==1

def test_stock_concurrent_orders(app):
    from concurrent.futures import ThreadPoolExecutor
    clients=[app.test_client(),app.test_client()]
    for n,c in enumerate(clients): register(c,f'user{n}@example.test');cart(c,[{'product_id':1,'quantity':1}])
    with connect(app.config['DATABASE']) as db: db.execute('UPDATE products SET stock=1 WHERE id=1')
    with ThreadPoolExecutor(max_workers=2) as pool: results=list(pool.map(order,clients))
    assert sorted(r.status_code for r in results)==[201,409]
    with connect(app.config['DATABASE']) as db: assert db.execute('SELECT stock FROM products WHERE id=1').fetchone()[0]==0
