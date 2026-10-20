"""Sprout: local, synthetic-data grocery demo. No real commerce."""
import hashlib
import re
import secrets
import sqlite3
import time
from pathlib import Path
from functools import wraps
from flask import Flask, request, jsonify, g, send_from_directory
from werkzeug.security import generate_password_hash, check_password_hash

CATALOG = [
 ('Farm fresh bananas','Produce','6 pieces',4900,48,'banana'),('Crisp red apples','Produce','4 pieces',12900,35,'apple'),('Garden tomatoes','Produce','500 g',3500,60,'tomato'),('Baby spinach','Produce','200 g',4500,30,'leaf'),
 ('Whole milk','Dairy','1 litre',6600,50,'milk'),('Greek yogurt','Dairy','400 g',11500,30,'yogurt'),('Salted butter','Dairy','100 g',5800,40,'butter'),('Fresh paneer','Dairy','200 g',9500,25,'paneer'),
 ('Sourdough loaf','Bakery','400 g',14900,18,'bread'),('Butter croissants','Bakery','2 pieces',9900,20,'croissant'),('Rolled oats','Pantry','500 g',8900,45,'oats'),('Basmati rice','Pantry','1 kg',13500,40,'rice'),
 ('Cold brew coffee','Drinks','250 ml',12500,35,'coffee'),('Orange juice','Drinks','1 litre',11000,28,'orange'),('Sparkling water','Drinks','750 ml',7500,40,'water'),('Dark chocolate','Snacks','80 g',9900,30,'chocolate'),
 ('Sea salt crisps','Snacks','100 g',4500,32,'crisps'),('Roasted almonds','Snacks','200 g',19900,25,'almond'),('Avocados','Produce','2 pieces',17900,16,'avocado'),('Free-range eggs','Dairy','6 pieces',7900,30,'egg')]

def connect(path):
    c=sqlite3.connect(path,timeout=10)
    c.row_factory=sqlite3.Row
    c.execute('PRAGMA foreign_keys=ON')
    return c

def initialize(path):
    Path(path).parent.mkdir(parents=True,exist_ok=True)
    with connect(path) as c:
        c.executescript(Path(__file__).with_name('schema.sql').read_text())
        if not c.execute('SELECT 1 FROM products LIMIT 1').fetchone():
            c.executemany('INSERT INTO products(name,category,unit,price,stock,art) VALUES(?,?,?,?,?,?)',CATALOG)

def create_app(config=None):
    app=Flask(__name__,static_folder='static',static_url_path='/static')
    app.config.update(DATABASE=str(Path('instance/sprout.sqlite').resolve()),MAX_CONTENT_LENGTH=32768,COOKIE_SECURE=False,TRUSTED_HOSTS=['localhost','127.0.0.1'])
    app.config.update(config or {})
    initialize(app.config['DATABASE'])
    attempts={}
    def db():
        if 'db' not in g: g.db=connect(app.config['DATABASE'])
        return g.db
    @app.teardown_appcontext
    def close(_):
        if 'db' in g: g.db.close()
    def fail(message,status=400): return jsonify(error=message),status
    def json_body():
        data=request.get_json(silent=True)
        return data if isinstance(data,dict) else {}
    def user():
        return db().execute('SELECT id,name,email,role FROM users WHERE id=?',(g.session['user_id'],)).fetchone()
    def require(admin=False):
        def decorator(fn):
            @wraps(fn)
            def wrapped(*args,**kwargs):
                u=user()
                if not u: return fail('Sign in to continue.',401)
                if admin and u['role']!='admin': return fail('Admin access required.',403)
                g.user=u
                return fn(*args,**kwargs)
            return wrapped
        return decorator
    def new_session(uid=None):
        raw=secrets.token_urlsafe(32); csrf=secrets.token_urlsafe(24)
        hashed=hashlib.sha256(raw.encode()).hexdigest()
        db().execute('INSERT INTO sessions VALUES(?,?,?,?)',(hashed,uid,csrf,int(time.time())+43200))
        db().commit(); g.new_cookie=raw
        g.session=dict(token_hash=hashed,user_id=uid,csrf=csrf)
    @app.before_request
    def before():
        if not request.path.startswith('/api/'): return
        raw=request.cookies.get('sprout_session','')
        hashed=hashlib.sha256(raw.encode()).hexdigest()
        g.session=db().execute('SELECT * FROM sessions WHERE token_hash=? AND expires>?',(hashed,int(time.time()))).fetchone()
        if g.session is None: new_session()
        if request.method not in ('GET','HEAD','OPTIONS'):
            if not secrets.compare_digest(request.headers.get('X-CSRF-Token',''),g.session['csrf']): return fail('Session expired. Reload and try again.',403)
            if request.headers.get('Origin') and request.headers['Origin']!=request.host_url.rstrip('/'): return fail('Cross-origin write refused.',403)
    @app.after_request
    def headers(response):
        if getattr(g,'new_cookie',None): response.set_cookie('sprout_session',g.new_cookie,httponly=True,samesite='Strict',secure=app.config['COOKIE_SECURE'],max_age=43200)
        response.headers['Content-Security-Policy']="default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; object-src 'none'; base-uri 'self'; frame-ancestors 'none'; form-action 'self'"
        response.headers['X-Content-Type-Options']='nosniff'
        response.headers['Referrer-Policy']='no-referrer'
        if request.path.startswith('/api/'): response.headers['Cache-Control']='no-store'
        return response
    @app.errorhandler(413)
    def large(_): return fail('Request is too large.',413)
    @app.errorhandler(404)
    def missing(_): return fail('Not found.',404)
    @app.get('/')
    def index(): return send_from_directory(app.static_folder,'index.html')
    @app.get('/api/session')
    def session():
        u=user()
        return jsonify(user=dict(u) if u else None,csrf=g.session['csrf'])
    def limited():
        key=request.remote_addr or 'unknown'; now=time.time()
        attempts[key]=[x for x in attempts.get(key,[]) if now-x<60]
        if len(attempts[key])>=20: return True
        attempts[key].append(now); return False
    def rotate(uid):
        db().execute('DELETE FROM sessions WHERE token_hash=?',(g.session['token_hash'],)); new_session(uid)
        return jsonify(user=dict(user()),csrf=g.session['csrf'])
    @app.post('/api/register')
    def register():
        if limited(): return fail('Too many attempts. Try again in a minute.',429)
        d=json_body(); name=d.get('name',''); email=d.get('email',''); password=d.get('password','')
        if not all(isinstance(x,str) for x in (name,email,password)): return fail('Invalid account details.')
        name=name.strip(); email=email.strip().lower()
        if not 2<=len(name)<=60 or not re.fullmatch(r'[^\s@]{1,100}@[^\s@]{1,100}\.[^\s@]{2,30}',email) or not 10<=len(password)<=128: return fail('Use a name, valid email and a password of 10–128 characters.')
        try:
            cur=db().execute('INSERT INTO users(name,email,password_hash) VALUES(?,?,?)',(name,email,generate_password_hash(password)))
            uid=cur.lastrowid; db().commit()
        except sqlite3.IntegrityError: return fail('Account already exists. Sign in instead.',409)
        return rotate(uid)
    @app.post('/api/login')
    def login():
        if limited(): return fail('Too many attempts. Try again in a minute.',429)
        d=json_body(); email=d.get('email',''); password=d.get('password','')
        if not isinstance(email,str) or not isinstance(password,str) or len(password)>128: return fail('Invalid credentials.',401)
        u=db().execute('SELECT * FROM users WHERE email=?',(email.strip().lower(),)).fetchone()
        if not u or not check_password_hash(u['password_hash'],password): return fail('Email or password is incorrect.',401)
        return rotate(u['id'])
    @app.post('/api/logout')
    def logout():
        db().execute('DELETE FROM sessions WHERE token_hash=?',(g.session['token_hash'],)); new_session()
        return jsonify(ok=True,csrf=g.session['csrf'])
    @app.get('/api/products')
    def products():
        q=request.args.get('q','')[:100].strip().lower(); cat=request.args.get('category','')
        rows=db().execute('SELECT * FROM products ORDER BY id').fetchall()
        return jsonify(products=[dict(p) for p in rows if (not q or q in p['name'].lower()) and (not cat or p['category']==cat)])
    @app.get('/api/cart')
    @require()
    def cart_get(): return jsonify(items=[dict(r) for r in db().execute('SELECT product_id,quantity FROM cart WHERE user_id=?',(g.user['id'],))])
    @app.put('/api/cart')
    @require()
    def cart_put():
        items=json_body().get('items')
        if not isinstance(items,list) or len(items)>50: return fail('Invalid cart.')
        seen=set()
        for i in items:
            if not isinstance(i,dict) or type(i.get('product_id')) is not int or type(i.get('quantity')) is not int or not 1<=i['quantity']<=20 or i['product_id'] in seen: return fail('Invalid cart quantity or duplicate item.')
            seen.add(i['product_id'])
            p=db().execute('SELECT stock FROM products WHERE id=?',(i['product_id'],)).fetchone()
            if not p: return fail('Product not found.',404)
        with db():
            db().execute('DELETE FROM cart WHERE user_id=?',(g.user['id'],))
            db().executemany('INSERT INTO cart VALUES(?,?,?)',[(g.user['id'],i['product_id'],i['quantity']) for i in items])
        return jsonify(ok=True)
    def orders_for(uid=None):
        rows=db().execute('SELECT o.*,u.name customer FROM orders o JOIN users u ON u.id=o.user_id '+('WHERE user_id=? ' if uid else '')+'ORDER BY o.id DESC', (uid,) if uid else ()).fetchall()
        result=[]
        for row in rows:
            o=dict(row); o['items']=[dict(i) for i in db().execute('SELECT name,unit,price,quantity FROM order_items WHERE order_id=?',(o['id'],))]; result.append(o)
        return result
    @app.get('/api/orders')
    @require()
    def orders(): return jsonify(orders=orders_for(g.user['id']))
    @app.post('/api/orders')
    @require()
    def place_order():
        d=json_body(); address=d.get('address',''); key=d.get('request_key','')
        if not isinstance(address,str) or not 10<=len(address.strip())<=300 or not isinstance(key,str) or not re.fullmatch(r'[a-zA-Z0-9_-]{16,80}',key): return fail('Enter a demo address (10–300 characters) and valid request key.')
        c=db()
        try:
            c.execute('BEGIN IMMEDIATE')
            existing=c.execute('SELECT id FROM orders WHERE user_id=? AND request_key=?',(g.user['id'],key)).fetchone()
            if existing:
                c.rollback(); return jsonify(id=existing['id'],replayed=True)
            items=c.execute('SELECT p.*,c.quantity FROM cart c JOIN products p ON p.id=c.product_id WHERE c.user_id=?',(g.user['id'],)).fetchall()
            if not items: c.rollback(); return fail('Your basket is empty.')
            if any(i['quantity']>i['stock'] for i in items): c.rollback(); return fail('Stock changed. Reduce the quantity and try again.',409)
            total=sum(i['price']*i['quantity'] for i in items)
            oid=c.execute('INSERT INTO orders(user_id,request_key,address,total) VALUES(?,?,?,?)',(g.user['id'],key,address.strip(),total)).lastrowid
            for i in items:
                c.execute('UPDATE products SET stock=stock-? WHERE id=?',(i['quantity'],i['id']))
                c.execute('INSERT INTO order_items VALUES(?,?,?,?,?,?)',(oid,i['id'],i['name'],i['unit'],i['price'],i['quantity']))
            c.execute('DELETE FROM cart WHERE user_id=?',(g.user['id'],)); c.commit()
            return jsonify(id=oid,total=total),201
        except Exception:
            c.rollback(); raise
    @app.get('/api/admin')
    @require(admin=True)
    def admin(): return jsonify(orders=orders_for(),products=[dict(p) for p in db().execute('SELECT * FROM products')])
    @app.patch('/api/admin/products/<int:pid>')
    @require(admin=True)
    def product_update(pid):
        d=json_body(); price=d.get('price'); stock=d.get('stock')
        if type(price) is not int or not 1<=price<=10000000 or type(stock) is not int or not 0<=stock<=10000: return fail('Price must be integer paise; stock must be 0–10000.')
        with db():
            if not db().execute('UPDATE products SET price=?,stock=? WHERE id=?',(price,stock,pid)).rowcount: return fail('Product not found.',404)
        return jsonify(ok=True)
    @app.patch('/api/admin/orders/<int:oid>')
    @require(admin=True)
    def order_update(oid):
        stages=['Demo placed','Demo packed','Demo completed']; status=json_body().get('status')
        o=db().execute('SELECT status FROM orders WHERE id=?',(oid,)).fetchone()
        if not o: return fail('Order not found.',404)
        if status not in stages or stages.index(status)!=stages.index(o['status'])+1: return fail('Only the next demo stage is allowed.')
        with db(): db().execute('UPDATE orders SET status=? WHERE id=?',(status,oid))
        return jsonify(ok=True)
    return app
