from flask import Flask, render_template, request, redirect
from flask import json as flask_json
from dataclasses import dataclass
from urllib.parse import urlparse
from hashlib import md5
from time import time
import requests
import json
import asyncio
import os
import sys
from functools import lru_cache
import cachetools

ttl_cache = cachetools.TTLCache(maxsize=2048, ttl=31 * 24 * 60 * 60)


app = Flask(__name__)
MEMEGEN_API = "http://api:5000"


@dataclass
class MemeTemplate:
    image_url: str
    name: str
    nb_lines: int
    extension: str


@lru_cache(maxsize=None)
def get_templates_list():
    _templates_list = dict()
    r = requests.get(MEMEGEN_API + "/images/")
    l = [x["template"] for x in json.loads(r.text)]
    l = [urlparse(x).path for x in l]
    for p in l:
        r = requests.get(MEMEGEN_API + p)
        temp = json.loads(r.text)
        img_url = urlparse(temp["blank"]).path
        img_url = "/api" + img_url
        ext = os.path.splitext(img_url)[-1].replace(".", "")
        name = temp["name"]
        if name.strip() == "":
            name = temp["id"]
        _templates_list[temp["id"]] = MemeTemplate(img_url, name, temp["lines"], ext)
    return _templates_list



@app.route('/', methods=["GET"])
def index():
    return render_template('index.html', templates_list=get_templates_list())

@app.route('/edit/<string:template_name>', methods=["GET"])
def edit(template_name):
    templates_list = get_templates_list()
    if not template_name in templates_list.keys():
        return 404
    template = templates_list[template_name]
    base_url = request.host_url
    return render_template('edit.html', template=template, id=template_name)

@app.route('/upload', methods=["POST"])
def upload():
    return 404
    # TODO upload the template
    # get_templates_list.cache_clear()
    # return render_template('index.html', message="Your template was uploaded")

@app.route('/shorten', methods=["GET"])
def shorten():
    global ttl_cache
    p = request.args.get("path")
    tag = md5((str(time()) + p).encode()).hexdigest()
    ttl_cache[tag] = p
    return flask_json.dumps({'path': p, 'tag': tag})

@app.route('/meme/<string:tag>', methods=["GET"])
def short_redirect(tag):
    global ttl_cache
    p = ttl_cache[tag]
    return redirect(p, code=302)

if __name__ == '__main__':
    # To get the cache warm
    get_templates_list()
    app.run(port=5001)