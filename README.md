# flippy

A from-scratch python serial controller for Hanover's flip-dot bus signs!
*(specifically the category of sign that display a bitmap image, not the ones that just do text)*

## setup
```shell
python -m venv .venv
. .venv/bin/activate # (linux)
python -m pip install -r requirements.txt
python -m demo [port] [w] [h]
```

## project structure
- `flippy/`: driver code, text handling
- `demo/`: various examples of what you can use the boards for, run `python -m demo [port] [w] [h]` to pick from them
- `utils/`: helper functionality for demos
- `server/`: web server for the board
