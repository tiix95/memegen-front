from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, make_response, send_file
from dataclasses import dataclass
from urllib.parse import urlparse
from hashlib import md5
import requests
import json
import asyncio
import os
import sys
import base64
from schema import Schema, SchemaError, Optional, And
import yaml
from jinja2 import Template
from functools import lru_cache
import cachetools
import magic
import string
import random
import time
from PIL import Image


url_shortener_dict = cachetools.LRUCache(maxsize=2048)
overlays_dict = cachetools.LRUCache(maxsize=64)

config_schema = Schema({
    "name": str,
    "text": [{
        "style": str,
        "color": str,
        "font": str,
        "anchor_x": And(float, lambda x: 0<=x<=1),
        "anchor_y": And(float, lambda x: 0<=x<=1),
        "angle": And(float, lambda x: -181<=x<=181),
        "scale_x": And(float, lambda x: 0<=x<=1),
        "scale_y": And(float, lambda x: 0<=x<=1),
        "align": str,
        "start": And(float, lambda x: 0<=x<=1),
        "stop": And(float, lambda x: 0<=x<=1)
    }],
    "example": [str],
    Optional("overlay"): [{
        "center_x": And(float, lambda x: 0<=x<=1),
        "center_y": And(float, lambda x: 0<=x<=1),
        "angle": And(float, lambda x: -181<=x<=181),
        "scale": And(float, lambda x: 0<=x<=1)
    }]
})


app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 4*1000*1000
app.secret_key = random.choices(population=string.ascii_letters, k=32)
MEMEGEN_API = "http://api:5000"
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}
ALLOWED_MIMETYPES = {'image/png', 'image/jpeg'}
TEMPLATES_DIR = "/app/memes/templates"
MINI_SIZE_MAX = 200


@dataclass
class MemeTemplate:
    image_url: str
    mini_image_url: str
    name: str
    nb_lines: int
    nb_overlays: int
    extension: str

@dataclass
class Overlay:
    content: str
    mime: str


def compress(template_name):
    def resize_max(_s):
        _x, _y = _s
        m = max(_x, _y)
        if m > MINI_SIZE_MAX:
            ratio = MINI_SIZE_MAX / m
            _x = round(_x*ratio)
            _y = round(_y*ratio)
        return _x, _y
    # Check if template_name exists
    if template_name in os.listdir(TEMPLATES_DIR):
        dirlist = os.listdir(os.path.join(TEMPLATES_DIR, template_name))
        if not 'mini.jpeg' in dirlist:
            filename = [x for x in dirlist if x.startswith("default.")][0]
            filepath = os.path.join(TEMPLATES_DIR, template_name, filename)
            image = Image.open(filepath)
            new_s = resize_max(image.size)
            image.resize(new_s)
            jpeg_image = image.convert('RGB')
            jpeg_image.save(os.path.join(TEMPLATES_DIR, template_name, "mini.jpeg"), "JPEG", optimize = True, quality = 40)
        return True
    else:
        return False

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
        mini_img_url = "/mini/" + base64.urlsafe_b64encode(temp["id"].encode()).decode().strip('=')
        ext = os.path.splitext(img_url)[-1].replace(".", "")
        name = temp["name"]
        if name.strip() == "":
            name = temp["id"]
        _templates_list[temp["id"]] = MemeTemplate(img_url, mini_img_url, name, temp["lines"], temp["overlays"], ext)
    return _templates_list

def filter_path_to_shorten(p):
    for c in list("' \n&%#\\<>\"+\t{}()[]:") + ["..", "//"]:
        if c in p:
            return False
    if not p.startswith('/api/images/'):
        return False
    return True


@app.route('/', methods=["GET"])
def index():
    return render_template('index.html', templates_list=get_templates_list())

@app.route('/mini/<string:_template_name>', methods=["GET"])
def mini(_template_name):
    template_name = base64.urlsafe_b64decode(_template_name + '=' * (-len(_template_name) % 4)).decode()
    template_exists = compress(template_name)
    if template_exists:
        return send_file(os.path.join(TEMPLATES_DIR, template_name, "mini.jpeg"), mimetype='image/jpeg')
    return "Not Found", 404


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
        return render_template('upload.html')
    elif request.method == "POST":
        # Validation of tag
        _tag = request.form.get("tag")
        if not (isinstance(_tag, str) and len(_tag) < 30 and all(c in string.ascii_lowercase for c in _tag) and not (_tag in os.listdir(TEMPLATES_DIR))):
            flash("Tag is not valid", category="danger")
            return redirect(url_for('upload'))

        # Validation of name
        _name = request.form.get("longname")
        if not isinstance(_name, str) and len(_name) < 1000:
            flash("Long name is not valid", category="danger")
            return redirect(url_for('upload'))
        
        # Validation of image
        if not "imgInp" in request.files.keys():
            flash("No file was given", category="danger")
            return redirect(url_for('upload'))
        _img = request.files["imgInp"]
        _img_content = _img.read()
        mime = magic.Magic(mime=True)
        if not ('.' in _img.filename and _img.filename.rsplit('.')[-1].lower() in ALLOWED_EXTENSIONS and mime.from_buffer(_img_content) in ALLOWED_MIMETYPES):
            flash("Image file not valid", category="danger")
            return redirect(url_for('upload'))
        _filename = "default." + _img.filename.rsplit('.')[-1].lower()
        
        try:
            _text_blocks = []
            for i in range(len(request.form.getlist('textInputStyle[]'))):
                d = dict()
                d["style"] = request.form.getlist('textInputStyle[]')[i]
                d["color"] = request.form.getlist('textInputColor[]')[i]
                d["font"] = request.form.getlist('textInputFont[]')[i]
                d["anchor_x"] = str(float(request.form.getlist('textInputAnchorX[]')[i]))
                d["anchor_y"] = str(float(request.form.getlist('textInputAnchorY[]')[i]))
                d["scale_x"] = str(float(request.form.getlist('textInputScaleX[]')[i]))
                d["scale_y"] = str(float(request.form.getlist('textInputScaleY[]')[i]))
                d["angle"] = str(float(request.form.getlist('textInputAngle[]')[i]))
                d["align"] = request.form.getlist('textInputAlignment[]')[i]
                d["example"] = request.form.getlist('textInputExample[]')[i]
                if not d in _text_blocks:
                    _text_blocks.append(d)
            
            _overlays = []
            if "boolOverlay" in request.form.keys() and request.form.get("boolOverlay") == "on":
                for i in range(len(request.form.getlist('overlayCenterX[]'))):
                    d = dict()
                    d["center_x"] = str(float(request.form.getlist('overlayCenterX[]')[i]))
                    d["center_y"] = str(float(request.form.getlist('overlayCenterY[]')[i]))
                    d["scale"] = str(float(request.form.getlist('overlayScale[]')[i]))
                    d["angle"] = str(float(request.form.getlist('overlayAngle[]')[i]))
                    if not d in _overlays:
                        _overlays.append(d)

            with open("/app/meme_config.yml.j2", "r") as f:
                tmplt = Template(f.read())
            _yml = tmplt.render(name=_name, text_blocks=_text_blocks, overlays=_overlays)
            print(_yml, file=sys.stderr, flush=True)
            configuration = yaml.safe_load(_yml)
            config_schema.validate(configuration)
        except Exception as e:
            print(e, file=sys.stderr, flush=True)
            flash("Yaml not valid, see documentation", category="danger")
            return redirect(url_for('upload'))

        os.mkdir(f'/app/memes/templates/{_tag}', mode=0o755)
        with open(f'/app/memes/templates/{_tag}/{_filename}', 'wb+') as f:
            f.write(_img_content)
        with open(f'/app/memes/templates/{_tag}/config.yml', 'w+') as f:
            f.write(_yml)

        get_templates_list.cache_clear()
        flash("Your template was uploaded ! Go check it out <a href=\"" + url_for('create', template_name=_tag) + "\">here !</a>")
        return redirect(url_for('index'))
    
    return 404

@app.route('/shorten', methods=["GET"])
def shorten():
    # Maybe Open Redirect here ? Maybe not ?
    global url_shortener_dict
    p = request.args.get("path")
    p = base64.urlsafe_b64decode(p + '=' * (-len(p) % 4)).decode('utf-8')
    print("aaa", file=sys.stderr, flush=True)
    if filter_path_to_shorten(p):
        print("bbb", file=sys.stderr, flush=True)
        tag = base64.urlsafe_b64encode(md5(p.encode()).digest()).decode().strip('=')
        url_shortener_dict[tag] = p
        return jsonify({'path': p, 'tag': tag})
    else:
        print("ccc", file=sys.stderr, flush=True)
        return "Unauthorized", 403

@app.route('/meme/<string:tag>', methods=["GET"])
def short_redirect(tag):
    global url_shortener_dict
    if tag in url_shortener_dict.keys():
        p = url_shortener_dict[tag]
        return redirect(p, code=302)
    flash("Meme not found, sorry", category="danger")
    return redirect(url_for('index'))

@app.route('/overlay', methods=["POST"])
def overlay_upload():
    global overlays_dict
    _img = request.files["overlay"]
    _img_content = _img.read()
    name = md5(_img_content).hexdigest()
    if not name in overlays_dict.keys():
        mime = magic.Magic(mime=True)
        mtype = mime.from_buffer(_img_content)
        if not mtype in ALLOWED_MIMETYPES:
            return 404
    
        o = Overlay(content=_img_content, mime=mtype)
        overlays_dict[name] = o
    return jsonify({"tag": name})

@app.route('/overlay/<string:tag>', methods=["GET"])
def overlay(tag):
    global overlays_dict
    if tag in overlays_dict.keys():
        p = overlays_dict[tag]
        r = make_response(p.content, 200)
        r.mimetype = p.mime
        return r
    # TODO return an image saying overlay not found
    flash("Overlay not found, sorry", category="danger")
    return redirect(url_for('index'))


if __name__ == '__main__':
    # To get the cache warm
    get_templates_list()
    app.run(port=5001)