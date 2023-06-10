from flask import Flask, render_template, request
from dataclasses import dataclass
from urllib.parse import urlparse
import requests
import json
import asyncio
import os
import sys
from functools import lru_cache

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

@app.route('/create/<string:template_name>', methods=["GET"])
def create(template_name):
    templates_list = get_templates_list()
    if not template_name in templates_list.keys():
        return 404
    template = templates_list[template_name]
    base_url = request.host_url
    return render_template('create.html', template=template, id=template_name, base_url=base_url.rstrip('/'))

@app.route('/upload', methods=["GET", "POST"])
def upload():
    if request.method == "GET":
        return render_template('upload.html')
    return 404
    
    # TODO upload the template
    # get_templates_list.cache_clear()
    # return render_template('upload.html', message="Your template was uploaded")

@app.route('/upload_doc', methods=["GET"])
def doc():
    return render_template('upload_doc.html')

if __name__ == '__main__':
    # To get the cache warm
    get_templates_list()
    app.run(port=5001)