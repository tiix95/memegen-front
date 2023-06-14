from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from dataclasses import dataclass
from urllib.parse import urlparse
from hashlib import md5
import requests
import json
import asyncio
import os
import sys
import base64
import yaml
from functools import lru_cache
import cachetools
import magic
import string
import random


ttl_cache = cachetools.TTLCache(maxsize=4096, ttl=31 * 24 * 60 * 60)


app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 8*1000*1000
app.secret_key = random.choices(population=string.ascii_letters, k=32)
MEMEGEN_API = "http://api:5000"
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}
ALLOWED_MIMETYPES = {'image/png', 'image/jpeg'}


@dataclass
class MemeTemplate:
    image_url: str
    name: str
    nb_lines: int
    nb_overlays: int
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
        _templates_list[temp["id"]] = MemeTemplate(img_url, name, temp["lines"], temp["overlays"], ext)
    return _templates_list

def filter_path_to_shorten(p):
    if "//" in p:
        return False
    for c in " \n?&%#\\<>\"":
        if c in p:
            return False
    if not p.startswith('/api/images/'):
        return False
    return True


@app.route('/', methods=["GET"])
def index():
    return render_template('index.html', templates_list=get_templates_list())

@app.route('/create/<string:template_name>', methods=["GET"])
def create(template_name):
    templates_list = get_templates_list()
    if not template_name in templates_list.keys():
        return 404
    template = templates_list[template_name]
    base_url = request.host_url
    return render_template('create.html', template=template, id=template_name)

@app.route('/upload', methods=["GET", "POST"])
def upload():
    if request.method == "GET":
        with open("/app/default_meme_config.yml", "r") as f:
            return render_template('upload.html', default_config=f.read())
        return 500
    elif request.method == "POST":
        # TODO add shitton of checks to check if the file is in the request etc etc

        # Validation of tag
        _tag = request.form.get("tag")
        if not (isinstance(_tag, str) and len(_tag) < 30 and all(c in string.ascii_lowercase for c in _tag) and not (_tag in os.listdir("/app/memes/templates"))):
            flash("Tag is not valid", category="danger")
            return redirect(url_for('upload'))
        
        # Validation of image
        _img = request.files["imgInp"]
        _img_content = _img.read()
        mime = magic.Magic(mime=True)
        if not ('.' in _img.filename and _img.filename.rsplit('.')[-1].lower() in ALLOWED_EXTENSIONS and mime.from_buffer(_img_content) in ALLOWED_MIMETYPES):
            flash("Image file not valid", category="danger")
            return redirect(url_for('upload'))
        _filename = "default." + _img.filename.rsplit('.')[-1].lower()
        
        # Validation of config.yml
        _yml = request.form.get("yml")
        # TODO validate yaml file structure with schema & pyyaml

        os.mkdir(f'/app/memes/templates/{_tag}', mode=0o755)
        with open(f'/app/memes/templates/{_tag}/{_filename}', 'wb+') as f:
            f.write(_img_content)
        with open(f'/app/memes/templates/{_tag}/config.yml', 'w+') as f:
            f.write(_yml)

        get_templates_list.cache_clear()
        flash("Your template was uploaded ! Go check it out <a href=\"" + url_for('create', template_name=_tag) + "\">here !</a>")
        return redirect(url_for('index'))
    
    return 404

@app.route('/upload_doc', methods=["GET"])
def doc():
    return render_template('upload_doc.html')

@app.route('/shorten', methods=["GET"])
def shorten():
    # Maybe Open Redirect here ? Maybe not ?
    global ttl_cache
    p = request.args.get("path")
    if filter_path_to_shorten(p):
        tag = base64.urlsafe_b64encode(md5(p.encode()).digest()).decode().strip('=')
        ttl_cache[tag] = p
        return jsonify({'path': p, 'tag': tag})
    else:
        return 403

@app.route('/meme/<string:tag>', methods=["GET"])
def short_redirect(tag):
    global ttl_cache
    if tag in ttl_cache.keys():
        p = ttl_cache[tag]
        return redirect(p, code=302)
    flash("Meme not found, sorry", category="danger")
    return redirect(url_for('index'))


if __name__ == '__main__':
    # To get the cache warm
    get_templates_list()
    app.run(port=5001)