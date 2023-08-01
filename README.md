# MemeGen All-in-One

## Some background on the project

Sometimes you just want to meme, but you don't want to send your meme data over the internet. Of course you could deploy the memegen repo directly, but it is only an API and does not provide a front-end interface. So I built one. Now, with just three commands, **you can meme fully on-premise** with a somewhat okay UX :)  
**ATTENTION** Note that I don't audit the memegen repo, and the local memegen instance could as well receive an update exfiltrating all the data to an external server, so please if you put it on premise, block outbound traffic. The server shouldn't leak any data as it is in a container network marked as "internal", but we're never too cautious. 

To be fair, this is mostly a one-night project. The code could be refactored, the UX is not that great, and there are a thousand things that could be done better. As one would say: it ain't much, but it's honest work. PRs are welcome !

## Installation

```bash
git clone --recurse-submodules https://github.com/Antoine-Gicquel/memegen-front.git
```

This project works great with the most recent versions of `podman compose` :

```bash
# In Debian repos since Debian 12
sudo apt install -y podman podman-compose
```

Else, you can use `docker` and `docker compose` (install as usual)

## Starting the meme generator

First, have a look at the `compose.yml` file. Here you can, among other things, customize the watermark which will be present on your memes via the `MEMEGEN_WATERMARK` environment variable.

Then, you can start the app using `podman`:

```bash
podman-compose build
podman-compose up
```
or
```bash
docker compose build
docker compose up
```

And let's meet on http://localhost:8080/ !
