import logging
from sys import argv
from argparse import ArgumentParser
from serial.tools.list_ports import comports

from demo.life import LifeDemo
from demo.lyrics import LyricsDemo
from demo.text import ClockDemo, TextDemo, MultiTextDemo
from flippy.comms import SerialComms
from flippy.sign import Sign


def list_ports(include_mock: bool = False):
    ports = sorted(comports())
    if len(ports) == 0 and not include_mock:
        print("No ports available - please connect the sign to your computer")
        return

    print("Available ports:")
    if include_mock:
        print(" MOCK: Mock port for testing (serial logged to console)")
    for port, desc, hwid in sorted(comports()):
        print(f" {port}: {desc} [{hwid}]")


if __name__ == "__main__":
    if len(argv) == 1:
        print("ERROR: You have not specified a port")
        list_ports()

    parser = ArgumentParser()
    parser.add_argument("port", help="port on which screen is connected")
    parser.add_argument("width", help="width of your screen")
    parser.add_argument("height", help="height of your screen")
    parser.add_argument("--address", default=0, help="display address")
    parser.add_argument("-v", "--verbose", default=False, action="store_true")
    args = parser.parse_args()

    if args.verbose:
        logging.basicConfig(level=logging.DEBUG)
    else:
        logging.basicConfig(level=logging.INFO)

    comms = SerialComms(port=args.port, address=args.address)
    sign = Sign(shape=(int(args.width), int(args.height)), comms=comms)

    demos = [TextDemo, ClockDemo, MultiTextDemo, LifeDemo, LyricsDemo]
    print("Demos Available:")
    for i, demo in enumerate(demos):
        print(f"{i:2}: {demo.__name__.replace('Demo', '')}")
    demo_idx = int(input("Choose an option index: "))
    if demo_idx < 0 or demo_idx >= len(demos):
        print("Error: Bad Index")
    else:
        demo = demos[demo_idx](sign, comms)
        demo.execute()
