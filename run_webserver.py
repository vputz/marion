#!venv/bin/python
from gevent.wsgi import WSGIServer
from werkzeug.serving import run_with_reloader
from werkzeug.debug import DebuggedApplication

from tutorial import app


@run_with_reloader
def run_server():
    http_server = WSGIServer(('', 5000), DebuggedApplication(app))
    http_server.serve_forever()

run_server()
