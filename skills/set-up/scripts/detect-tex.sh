#!/usr/bin/env bash
# detect-tex.sh — report which LaTeX engines and install tools are present.
#
# Usage: detect-tex.sh
#
# Emits a single JSON object on stdout describing:
#   os            — darwin | linux | windows | unknown
#   engines       — for each known engine: {present, path, version}
#   packageMgrs   — install tools available on this machine (brew, apt, winget, …)
#   recommend     — the install route this script suggests for the OS
#
# Pure shell, no network, never exits non-zero on a missing tool (a missing
# engine is the normal case this script exists to report). The set-up skill
# parses this to decide what to offer the user.

set -u

# --- OS ---------------------------------------------------------------------
uname_s="$(uname -s 2>/dev/null || echo unknown)"
case "$uname_s" in
  Darwin*)               OS="darwin" ;;
  Linux*)                OS="linux" ;;
  MINGW*|MSYS*|CYGWIN*)  OS="windows" ;;
  *)                     OS="unknown" ;;
esac

# --- helpers ----------------------------------------------------------------
# JSON-escape a string (backslash, quote, control chars).
json_escape() {
  printf '%s' "$1" | sed -e 's/\\/\\\\/g' -e 's/"/\\"/g' -e 's/	/\\t/g'
}

emit_engine() {
  # $1 = engine name, $2 = version flag (default --version).
  # TeX engines accept --version and print to stdout; Poppler's pdftoppm wants
  # -v and prints to stderr. We merge stderr (2>&1) so either form is captured.
  local name="$1" vflag="${2:---version}" path ver present
  if path="$(command -v "$name" 2>/dev/null)"; then
    present="true"
    ver="$("$name" "$vflag" 2>&1 | head -n1 | tr -d '\r')"
  else
    present="false"; path=""; ver=""
  fi
  printf '    "%s": {"present": %s, "path": "%s", "version": "%s"}' \
    "$name" "$present" "$(json_escape "$path")" "$(json_escape "$ver")"
}

has() { command -v "$1" >/dev/null 2>&1 && echo true || echo false; }

# --- engines ----------------------------------------------------------------
# latexmk is the orchestrator; the rest are PDF engines / bib tools / renderer.
echo "{"
printf '  "os": "%s",\n' "$OS"
echo '  "engines": {'
emit_engine latexmk;  echo ","
emit_engine pdflatex; echo ","
emit_engine xelatex;  echo ","
emit_engine lualatex; echo ","
emit_engine tectonic; echo ","
emit_engine bibtex;   echo ","
emit_engine biber;    echo ","
emit_engine pdftoppm '-v'; echo ","
emit_engine python3;  echo ","
emit_engine python
echo ""
echo "  },"

# --- package / install managers --------------------------------------------
echo '  "packageMgrs": {'
printf '    "brew": %s,\n'   "$(has brew)"
printf '    "port": %s,\n'   "$(has port)"
printf '    "apt-get": %s,\n' "$(has apt-get)"
printf '    "dnf": %s,\n'    "$(has dnf)"
printf '    "yum": %s,\n'    "$(has yum)"
printf '    "pacman": %s,\n' "$(has pacman)"
printf '    "zypper": %s,\n' "$(has zypper)"
printf '    "winget": %s,\n' "$(has winget)"
printf '    "scoop": %s,\n'  "$(has scoop)"
printf '    "choco": %s,\n'  "$(has choco)"
printf '    "tlmgr": %s,\n'  "$(has tlmgr)"
printf '    "curl": %s,\n'   "$(has curl)"
printf '    "wget": %s\n'    "$(has wget)"
echo "  },"

# --- recommended route ------------------------------------------------------
# What this script would suggest, given the OS and what's available.
recommend="tinytex"
case "$OS" in
  darwin)  [ "$(has brew)" = true ] && recommend="brew-mactex" ;;
  linux)
    if   [ "$(has apt-get)" = true ]; then recommend="apt"
    elif [ "$(has dnf)" = true ];     then recommend="dnf"
    elif [ "$(has pacman)" = true ];  then recommend="pacman"
    else recommend="tinytex"; fi ;;
  windows) [ "$(has winget)" = true ] && recommend="winget-miktex" ;;
esac
printf '  "recommend": "%s"\n' "$recommend"
echo "}"
