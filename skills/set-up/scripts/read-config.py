#!/usr/bin/env python
# read-config.py - read a value from the project's .latex-sentinel.json.
#
# compile-tex and visual-polish call this to learn how this paper builds.
# Searches the given start dir and every parent up to the filesystem root for
# .latex-sentinel.json (so it works when invoked from a subfolder), then prints
# one requested field. Prints nothing and exits 1 if no config / field is found,
# so callers can do:  CMD="$(read-config.py --field compileCommand --dir "$D")"
#
# Usage:
#   python read-config.py --field compileCommand [--dir .]
#   python read-config.py --field engine
#   python read-config.py --field tools.pdftoppm
#   python read-config.py --json            # dump the whole resolved config
#
# Stdlib only, no network. On systems whose binary is python3, substitute it.

import argparse
import json
import os
import sys

CONFIG_NAME = ".latex-sentinel.json"


def find_config(start):
    cur = os.path.abspath(start)
    while True:
        candidate = os.path.join(cur, CONFIG_NAME)
        if os.path.isfile(candidate):
            return candidate
        parent = os.path.dirname(cur)
        if parent == cur:  # hit filesystem root
            return None
        cur = parent


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", default=".")
    ap.add_argument("--field", default=None,
                    help="dotted key to print, e.g. compileCommand or tools.pdftoppm")
    ap.add_argument("--json", action="store_true", help="print whole config")
    ap.add_argument("--path", action="store_true", help="print config file path")
    args = ap.parse_args()

    path = find_config(args.dir)
    if not path:
        return 1
    try:
        with open(path, encoding="utf-8") as fh:
            config = json.load(fh)
    except (ValueError, OSError):
        return 1

    if args.path:
        print(path)
        return 0
    if args.json:
        print(json.dumps(config, indent=2, ensure_ascii=False))
        return 0
    if not args.field:
        return 1

    value = config
    for part in args.field.split("."):
        if isinstance(value, dict) and part in value:
            value = value[part]
        else:
            return 1
    if value is None:
        return 1
    print(value)
    return 0


if __name__ == "__main__":
    sys.exit(main())
