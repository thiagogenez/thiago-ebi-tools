#!/bin/bash
set -u

REPO="https://github.com/thiagogenez/ebi-utils"
PREFIX="$HOME/.ebi-utils"


#######################################################################################
#######################################################################################
# SCRIPT FROM  https://raw.githubusercontent.com/Homebrew/install/master/install.sh

shell_join() {
  local arg
  printf "%s" "$1"
  shift
  for arg in "$@"; do
    printf " "
    printf "%s" "${arg// /\ }"
  done
}

chomp() {
  printf "%s" "${1/"$'\n'"/}"
}


ohai() {
  printf "${tty_blue}==>${tty_bold} %s${tty_reset}\n" "$(shell_join "$@")"
}

abort() {
  printf "%s\n" "$1"
  exit 1
}

warn() {
  printf "${tty_red}Warning${tty_reset}: %s\n" "$(chomp "$1")"
}

execute() {
  if ! "$@"; then
    abort "$(printf "Failed during: %s" "$(shell_join "$@")")"
  fi
}


# string formatters
if [[ -t 1 ]]; then
  tty_escape() { printf "\033[%sm" "$1"; }
else
  tty_escape() { :; }
fi
tty_mkbold() { tty_escape "1;$1"; }
tty_underline="$(tty_escape "4;39")"
tty_blue="$(tty_mkbold 34)"
tty_red="$(tty_mkbold 31)"
tty_bold="$(tty_mkbold 39)"
tty_reset="$(tty_escape 0)"


if ! command -v git >/dev/null; then
    abort "$(cat <<EOABORT
You must install Git before installing EBI-Utils.
EOABORT
)"
fi

if ! command -v curl >/dev/null; then
    abort "$(cat <<EOABORT
You must install cURL before installing EBI-Utils. 
EOABORT
)"
fi



if [[ "$UID" == "0" ]]; then
  abort "Don't run this as root!"
elif [[ -d "$PREFIX" && ! -x "$PREFIX" ]]; then
  abort "$(cat <<EOABORT
The prefix, ${PREFIX}, exists but is not searchable. If this is
not intentional, please restore the default permissions and try running the
installer again:
    sudo chmod 775 ${PREFIX}
EOABORT
)"
fi
#######################################################################################
#######################################################################################

ohai "This script will install:"
echo "${PREFIX}"

if ! [[ -d "${PREFIX}" ]]; then
    execute "/bin/mkdir" "-p" "${PREFIX}"
fi

ohai "Downloading and installing EBI-Utils..."
(
  cd "${PREFIX}" >/dev/null || return

  # we do it in four steps to avoid merge errors when reinstalling
  execute "git" "clone" "$REPO"

) || exit 1

if [[ ":${PATH}:" != *":${PREFIX}/bin:"* ]]; then
  warn "${PREFIX}/bin is not in your PATH."
fi

ohai "Installation successful!"
echo

#######################################################################################