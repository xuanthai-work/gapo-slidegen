import argparse
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument("--slide")
parser.add_argument("--out")
args = parser.parse_args()
Path(args.out).write_bytes(b"nope")
