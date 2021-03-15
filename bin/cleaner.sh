#!/bin/bash

if [[ $# != 1 ]]; then
  echo "Wrong number of arguments. Usage: $(basename $0) <hostname-prefix>path"
  exit 0
fi

PREFIX=$1


spinner()
{
    local pid=$!
    local delay=0.75
    local spinstr='|/-\'
    while [ "$(ps a | awk '{print $1}' | grep $pid)" ]; do
        local temp=${spinstr#?}
        printf " [%c]  " "$spinstr"
        local spinstr=$temp${spinstr%"$temp"}
        sleep $delay
        printf "\b\b\b\b\b\b"
    done
    printf "    \b\b\b\b"
}

# sanity checkes
HOSTS=($(bhosts | grep $PREFIX | grep "ok\|closed" | awk '{print $1}'))
if [ -z "$HOSTS" ]; then 
  echo "Found any hostname starting with $PERFIX"
  exit 0
fi

# disable cursor
tput civis

for i in "${!HOSTS[@]}"; do
  printf "pruning at ${HOSTS[i]} ... "
  eval "ssh -q ${HOSTS[$i]} 'bash $PWD/pruner.sh' &"
 	spinner	
  printf " done\n"
done

# enable cursos
tput cnorm
