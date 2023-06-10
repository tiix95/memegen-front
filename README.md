# MemeGen All-in-One

## Some background on the project

Sometimes you just want to meme, but you don't want to send your meme data over the internet. Of course you could use memegen directly, but it is only an API and does not provide a front-end. So I built one, and while I'm at it, I also handled the local deployment for you, with an nginx reverse proxy. So now, with just three commands, **you can meme fully on-premise** :)  
**ATTENTION** Note that I don't control the memegen repo, and the local memegen instance could as well receive an update that make it return a webpage containing a Google Analytics tag or any other tracker, so please if you put it on premise, block outbound traffic to Google when looking at a meme. It is on my TODO-list to break these tags on the fly with Nginx.  

To be fair, this is a one-night project. The code could be refactored, the UX is not that great, and there are a thousand things that could be done better. As one would say : it ain't much, but it's honest work.

## Installation

```bash
git clone --recurse-submodules https://github.com/Antoine-Gicquel/memegen-front.git
```

This project works great with `podman compose` :

```bash
# In Debian repos since Debian 12
sudo apt install -y podman podman-compose

# Else
sudo apt install -y podman python3 python3-pip
# If podman --version is smaller than 3.1
pip3 install podman-compose~=0.1
# Else
pip3 install podman-compose
```

## Starting the meme generator

```bash
podman-compose build
podman-compose up
```

And let's meet on http://localhost:8000/ !
