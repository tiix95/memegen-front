# MemeGen All-in-One

## Some background on the project

Blabla
Honnêtement c'est pas dingue comme code, l'UX est moins bien que imgflip, mais bon c'est on-premise et basé sur un tool déjà existant que j'ai pas à maintenir.

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