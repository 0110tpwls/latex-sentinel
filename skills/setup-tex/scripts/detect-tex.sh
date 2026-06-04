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
# engine is the normal case this script exists to report). The setup-tex skill
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

# First line of `<tool> --version`, trimmed; empty if it fails.
first_version_line() {
  "$1" --version 2>/dev/null | head -n1 | tr -d '\r'
}

emit_engine() {
  # $1 = engine name, $2 = version-flag form (--version vs -version)
  local name="$1" vflag="${2:---version}" path ver present
  if path="$(command -v "$name" 2>/dev/null)"; then
    present="true"
    if [ "$vflag" = "-version" ]; then
      ver="$("$name" -version 2>/dev/null | head -n1 | tr -d '\r')"
    else
      ver="$(first_version_line "$name")"
    fi
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
emit_engine pdftoppm '-version'
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
