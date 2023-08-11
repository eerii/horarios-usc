#import api.web

from pywebio.platform.flask import webio_view
from flask import Flask

app = Flask(__name__)
#app.add_url_rule('/horario', 'webio_view', webio_view(web.run), methods=['GET', 'POST', 'OPTIONS'])

@app.get('/')
def hello_world():
    return "Hello, World!"

@app.get('/hey')
def holuuu():
    return "Holuuuu"