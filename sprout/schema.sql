CREATE TABLE IF NOT EXISTS migrations(version INTEGER PRIMARY KEY);
INSERT OR IGNORE INTO migrations VALUES (1);
CREATE TABLE IF NOT EXISTS users(id INTEGER PRIMARY KEY, name TEXT NOT NULL, email TEXT UNIQUE NOT NULL, password_hash TEXT NOT NULL, role TEXT NOT NULL DEFAULT 'customer' CHECK(role IN ('customer','admin')));
CREATE TABLE IF NOT EXISTS sessions(token_hash TEXT PRIMARY KEY, user_id INTEGER REFERENCES users(id), csrf TEXT NOT NULL, expires INTEGER NOT NULL);
CREATE TABLE IF NOT EXISTS products(id INTEGER PRIMARY KEY,name TEXT NOT NULL,category TEXT NOT NULL,unit TEXT NOT NULL,price INTEGER NOT NULL CHECK(price>0),stock INTEGER NOT NULL CHECK(stock>=0),art TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS cart(user_id INTEGER REFERENCES users(id),product_id INTEGER REFERENCES products(id),quantity INTEGER NOT NULL CHECK(quantity BETWEEN 1 AND 20), PRIMARY KEY(user_id,product_id));
CREATE TABLE IF NOT EXISTS orders(id INTEGER PRIMARY KEY,user_id INTEGER NOT NULL REFERENCES users(id),request_key TEXT NOT NULL,address TEXT NOT NULL,total INTEGER NOT NULL,created TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ','now')),status TEXT NOT NULL DEFAULT 'Demo placed' CHECK(status IN ('Demo placed','Demo packed','Demo completed')), UNIQUE(user_id,request_key));
CREATE TABLE IF NOT EXISTS order_items(order_id INTEGER REFERENCES orders(id),product_id INTEGER,name TEXT,unit TEXT,price INTEGER,quantity INTEGER,PRIMARY KEY(order_id,product_id));
