import argparse
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument("--slide")
parser.add_argument("--out")
args = parser.parse_args()
Path(args.out).write_bytes(b"\x89PNG\r\n\x1a\n" + Path(args.slide).read_bytes()[:8])
