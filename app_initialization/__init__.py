from flask import Flask
from flask_cors import CORS
from flask_caching import Cache

app = Flask(__name__)
CORS(app)
app.config['CACHE_TYPE'] = 'simple'
cache = Cache(app)

from . import routes