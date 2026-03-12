import argparse
import sys
from typing import List, Optional

from ghost_blogger.runner import run_once


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(prog="ghost-blogger")
    sub = parser.add_subparsers(dest="cmd", required=True)

    run = sub.add_parser("run", help="Read sources and write a new Jekyll post.")
    run.add_argument("--config", required=True, help="Path to config YAML.")

    args = parser.parse_args(argv)
    if args.cmd == "run":
        run_once(args.config)
        return 0

    return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
