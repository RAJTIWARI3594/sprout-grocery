"""Create an isolated synthetic database/server, run E2E, then remove the DB."""
import os, sys, tempfile, threading, subprocess
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from sprout import create_app, connect
from werkzeug.security import generate_password_hash
from werkzeug.serving import make_server
with tempfile.TemporaryDirectory() as tmp:
    path=str(Path(tmp)/'browser.sqlite')
    app=create_app({'DATABASE':path})
    with connect(path) as c:
        c.execute('INSERT INTO users(name,email,password_hash,role) VALUES(?,?,?,?)',('Demo Admin','admin@example.test',generate_password_hash('Admin-demo-2026'),'admin'))
    server=make_server('127.0.0.1',0,app,threaded=True)
    thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
    try:
        result=subprocess.run([sys.executable,'tests/browser_check.py'],env={**os.environ,'SPROUT_TEST_URL':f'http://127.0.0.1:{server.server_port}'})
    finally: server.shutdown();thread.join()
    raise SystemExit(result.returncode)
