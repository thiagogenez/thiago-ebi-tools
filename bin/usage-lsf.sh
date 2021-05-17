#!/bin/bash

#####################
# PARSING ARGUMENTS
######################

POSITIONAL=()
while [[ $# -gt 0 ]]; do

  key="$1"

  case $key in
    
    -o|--output)
      CSV_FILE="$2"
      shift # past argument
      shift # past value
    ;;

    -h|--help)
      echo "$(cat <<EOF
Usage:  bash $(basename $0) [option]
Options:
  -o | --output: output filename
  -h | --help: to print this message
EOF
)"
      exit 0;
    ;;
    
    *)    # unknown option
      UNKNOWN+=("$1") # save it in an array for later
      shift # past argument
    ;;
  
  esac
done
set -- "${UNKNOWN[@]}" # restore UNKNOWN parameters

if [[ "${#UNKNOWN[@]}" -gt 0  ]]; then
  echo "Unknown arguments      = ${UNKNOWN[@]}"
  echo "Run \"bash $(basename $0) --help\" for more details" 
  exit 0
fi

if [[ "$CSV_FILE" == "" ]]; then
  echo "argument \"-o\" or \"--output\" is missing"
  exit 0
fi


echo "Given arguments:"
echo "  FILE CSV_FILE   = ${CSV_FILE}"


#####################
# ELAPSED FUNCTION
######################
get_elapsed_time(){
  echo "$SECONDS - $1" | bc -l
}


#start_time="$(date +%s.%N)"
start_time=$SECONDS

echo "TIME_SECONDS,TIME_FORMAT,CPU_USAGE,MEM_USAGE" >> $CSV_FILE

while true; do
  
  sleep 5
  

  MEM_USAGE=$(bjobs -l | grep "AVG MEM" | awk '{print $7}' | awk '{ sum += $1 } END {  print(sum ) }')
  CPU_USAGE=$(bjobs -w -noheader | grep RUN | wc -l)
  
  elapsed=$(get_elapsed_time $start_time)
  format_time=$(TZ=UTC0 printf '%(%H:%M:%S)T\n' "$elapsed")

  echo "$elapsed,$format_time,$CPU_USAGE,$$MEM_USAGE" >> $CSV_FILE
  

done

echo "$(basename $0) finalised"
exit 0
