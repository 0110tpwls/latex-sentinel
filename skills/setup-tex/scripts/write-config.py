#!/usr/bin/env python
# write-config.py - create or update a project-level .latex-sentinel.json.
#
# The config tells compile-tex / review-pipeline HOW to build this paper:
# which engine, the exact command, and where the PDF renderer lives. Storing
# it per-project (next to the .tex) means a XeLaTeX paper and a pdfLaTeX paper
# in different folders each compile correctly without re-asking.
#
# Usage:
#   python write-config.py --engine latexmk \
#       --command "latexmk -pdf -interaction=nonstopmode -halt-on-error -file-line-error" \
#       [--distribution tinytex] [--pdftoppm pdftoppm] [--dir .] [--print]
#
# Merges into an existing file (keys you don't pass are preserved). On systems
# whose binary is python3, substitute python3. Stdlib only, no network.

import argparse
import json
import os
import sys

CONFIG_NAME = ".latex-sentinel.json"
SCHEMA_VERSION = 1

# Engine -> default command, used when --command is omitted. latexmk variants
# pass the engine selector; tectonic is self-contained; raw engines get the
# standard nonstop/halt flags (compile-tex handles the multi-pass itself).
DEFAULT_COMMANDS = {
    "latexmk": "latexmk -pdf -interaction=nonstopmode -halt-on-error -file-line-error",
    "latexmk-xelatex": "latexmk -xelatex -interaction=nonstopmode -halt-on-error -file-line-error",
    "latexmk-lualatex": "latexmk -lualatex -interaction=nonstopmode -halt-on-error -file-line-error",
    "pdflatex": "pdflatex -interaction=nonstopmode -halt-on-error -file-line-error",
    "xelatex": "xelatex -interaction=nonstopmode -halt-on-error -file-line-error",
    "lualatex": "lualatex -interaction=nonstopmode -halt-on-error -file-line-error",
    "tectonic": "tectonic",
}


def main():
    ap = argparse.ArgumentParser(description="Write .latex-sentinel.json")
    ap.add_argument("--engine", required=True,
                    help="latexmk | latexmk-xelatex | latexmk-lualatex | "
                         "pdflatex | xelatex | lualatex | tectonic")
    ap.add_argument("--command", default=None,
                    help="exact compile command (the .tex path is appended). "
                         "Defaults to a sensible command for --engine.")
    ap.add_argument("--distribution", default=None,
                    help="informational: how TeX was installed (tinytex, "
                         "mactex, miktex, texlive, tectonic)")
    ap.add_argument("--pdftoppm", default=None,
                    help="path/name of the pdftoppm binary for visual-polish")
    ap.add_argument("--dir", default=".", help="project dir to write into")
    ap.add_argument("--print", action="store_true",
                    help="also print the resulting config to stdout")
    args = ap.parse_args()

    path = os.path.join(args.dir, CONFIG_NAME)

    # Load existing config so unspecified keys survive a re-run.
    config = {}
    if os.path.exists(path):
        try:
            with open(path, encoding="utf-8") as fh:
                config = json.load(fh)
            if not isinstance(config, dict):
                config = {}
        except (ValueError, OSError) as exc:
            print("write-config: existing %s is not valid JSON (%s); "
                  "overwriting." % (CONFIG_NAME, exc), file=sys.stderr)
            config = {}

    command = args.command or DEFAULT_COMMANDS.get(args.engine)
    if not command:
        print("write-config: no --command given and no default for engine "
              "'%s'." % args.engine, file=sys.stderr)
        return 2

    config["version"] = SCHEMA_VERSION
    config["engine"] = args.engine
    config["compileCommand"] = command
    if args.distribution:
        config["distribution"] = args.distribution

    tools = config.get("tools")
    if not isinstance(tools, dict):
        tools = {}
    if args.pdftoppm:
        tools["pdftoppm"] = args.pdftoppm
    if tools:
        config["tools"] = tools

    rendered = json.dumps(config, indent=2, ensure_ascii=False) + "\n"
    try:
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(rendered)
    except OSError as exc:
        print("write-config: could not write %s (%s)" % (path, exc),
              file=sys.stderr)
        return 1

    print("write-config: wrote %s" % path)
    if args.print:
        sys.stdout.write(rendered)
    return 0


if __name__ == "__main__":
    sys.exit(main())
