# Setup Commands

Start up process (for each process)

1. Attach to tmux session
2. Enter venv
3. Start process

## GitHub

### Clone repo

```bash
git clone https://github.com/rufusclark/Satellite-Propagation-Toolkit.git
```

### Update repo

```bash
git pull
```

### Reset/Update repo whilst discarding local changes

```bash
git fetch origin
git reset --hard origin/Satellite-Propagation-Toolkit
```

## tmux (Multiple persistent terminal windows)

[TMUX Docs](https://github.com/tmux/tmux/wiki/Getting-Started)

### create new tmux windows

```bash
tmux new -sapi_server
tmux new -scache_updater
```

### list tmux sessions

```bash
tmux ls
```

### attach to existing tmux windows

```bash
tmux attach -tapi_server
tmux attach -tcache_updater
```

### detach from tmux window

```C-b d``` key binding

## Python Virtual Environment (venv)

### Create venv

```bash
python3 -m venv venv
```

### Activate venv

```bash
source venv/bin/activate
```

### Deactivate venv

```bash
deactivate
```

## Python

### Install required libraries

```bash
pip install -r requirements.txt
```

## Running server components

### Run cache updator (from project root)

```bash
python3 ./unity/update_cache.py
```

### Run API (from project root)

```bash
waitress-serve --port=8000 unity.app:app
```
