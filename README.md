# flippy

A from-scratch python serial controller for Hanover's flip-dot bus signs!
*(specifically the category of sign that display a bitmap image, not the ones that just do text)*

## setup

Connect your display to 24V power and a modbus-to-USB adapter (I used a generic one, which seemed to work without any
issues). This should appear as a serial device on your computer - you can find the port it is connected to using the
command `python -m serial.tools.list_ports` (provided by pyserial).

The width and height of the display are as measured in pixels - if it doesn't appear to work correctly, try swapping
the two values with each other.

```shell
python -m venv .venv
. .venv/bin/activate # (linux)
python -m pip install -r requirements.txt
python -m demo [port] [w] [h]
```

### server
My driver also supports connecting to remote serial devices using the RFC2217 protocol - if you have one running, you
can use it as the port by passing `rfc2217://[hostname]:[port]`. For a simple RFC2217 server, look at the [example](https://github.com/pyserial/pyserial/blob/master/examples/rfc2217_server.py)
provided by pyserial (note: this script does not implement any security measures, use with caution on open networks)

## project structure
- `flippy/`: driver code, text handling
- `demo/`: various examples of what you can use the boards for, run `python -m demo [port] [w] [h]` to pick from them
- `utils/`: helper functionality for demos
