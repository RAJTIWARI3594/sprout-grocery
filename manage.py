"""Local development entrypoint and explicit admin creation."""
import argparse, getpass, os
from sprout import create_app, connect
from werkzeug.security import generate_password_hash
p=argparse.ArgumentParser(); p.add_argument('command',choices=['run','init-db','create-admin']); p.add_argument('--port',type=int,default=5057)
a=p.parse_args(); app=create_app({'DATABASE':os.getenv('SPROUT_DATABASE','instance/sprout.sqlite'),'COOKIE_SECURE':os.getenv('SPROUT_HTTPS')=='1'})
if a.command=='run': app.run(host='127.0.0.1',port=a.port,debug=False)
elif a.command=='create-admin':
    email=input('Admin email: ').strip().lower(); name=input('Admin name: ').strip(); password=getpass.getpass('New password (10+ characters): ')
    if not name or '@' not in email or not 10<=len(password)<=128: raise SystemExit('Invalid input')
    with connect(app.config['DATABASE']) as c: c.execute('INSERT INTO users(name,email,password_hash,role) VALUES(?,?,?,?)',(name,email,generate_password_hash(password),'admin'))
    print('Admin created. No default admin password is shipped.')
else: print('Database initialized; existing rows preserved.')
