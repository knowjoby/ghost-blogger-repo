import argparse
import sys
from typing import List, Optional

from ghost_blogger.runner import run_once


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(prog="ghost-blogger")
    sub = parser.add_subparsers(dest="cmd", required=True)

    run = sub.add_parser("run", help="Read sources and write a new Jekyll post.")
    run.add_argument("--config", required=True, help="Path to config YAML.")
    run.add_argument("--dry-run", action="store_true", default=False,
                     help="Print rendered post to stdout; skip file write and state update.")

    analyse = sub.add_parser("analyse", help="Analyse telemetry and write analysis.json")
    analyse.add_argument("--config", required=True)

    improve = sub.add_parser("improve", help="Apply safe config mutations based on analysis")
    improve.add_argument("--config", required=True)

    reflect = sub.add_parser("reflect", help="Write weekly reflection post")
    reflect.add_argument("--config", required=True)

    args = parser.parse_args(argv)

    if args.cmd == "run":
        run_once(args.config, dry_run=args.dry_run)
        return 0

    if args.cmd == "analyse":
        from ghost_blogger.analyst import analyse_once
        analyse_once(args.config)
        return 0

    if args.cmd == "improve":
        from ghost_blogger.improver import improve_once
        improve_once(args.config)
        return 0

    if args.cmd == "reflect":
        from ghost_blogger.reflector import reflect_once
        reflect_once(args.config)
        return 0

    return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
