#!/bin/bash

#####################
# PARSING ARGUMENTS
######################
GPU=NO

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
  -g | --gpu: to parse resource usage outputeed from nvidia-smi
EOF
)"
      exit 0;
    ;;

    -g|--gpu)
      GPU=YES
      shift # past argument
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


CSV_FILE_2="$(echo ${CSV_FILE})-top.txt"
echo "Given arguments:"
echo "  FILE CSV_FILE   = ${CSV_FILE}"
echo "  FILE CSV_FILE 2 = ${CSV_FILE_2}"
echo "  GPU             = ${GPU}"


#####################
# ELAPSED FUNCTION
######################
get_elapsed_time(){
  echo "$SECONDS - $1" | bc -l
}


#####################
# PARSING JOB
######################

start_time=$SECONDS

while true; do
  cactus_pid=$(ps axf | grep 'cactus-preprocess\|cactus-blast\|cactus-align\|run_segalign' | grep -v grep | awk '{print $1}')
  if [[ "$cactus_pid" != "" ]]; then
    echo "found PID=$cactus_pid"
    break
  fi
  sleep 1

  elapsed=$(get_elapsed_time $start_time)
  if [[ "$elapsed" -gt "30" ]]; then
    echo "Cactus PID not found, exiting with code 1"
    exit 1
  fi

done

#start_time="$(date +%s.%N)"
start_time=$SECONDS

if [[ "$GPU" == "YES" ]]; then
  echo "TIME_SECONDS,TIME_FORMAT,CPU_USAGE,CPU_USAGE2,GPU_USAGE,MEM_USAGE,GPU_MEM_USAGE" >> $CSV_FILE
  #nvidia filename
  NVIDIA_LOG="nvidia-$(hostname).log"
  [ -f $NVIDIA_LOG ] && rm $NVIDIA_LOG

else
  echo "TIME_SECONDS,TIME_FORMAT,CPU_USAGE,CPU_USAGE2,MEM_USAGE,CPU_CONSOLIDATED,MEMORY_CONSOLIDATED" >> $CSV_FILE
fi


while true; do
   
  if [[ "$GPU" == "YES" ]]; then
    # GPU parser is slower, so get it first
    nvidia-smi > $NVIDIA_LOG
    AMOUNT=$(nvidia-smi --query-gpu=name --format=csv,noheader | wc -l)
    GPU_USAGE=$(grep "%" $NVIDIA_LOG | awk '{print $13}' | cut -d'%' -f1  | awk '{ sum += $1 } END {  if (NR > 0) print(sum / NR) }')
    GPU_MEM_USAGE=$(grep "MiB" $NVIDIA_LOG | head -$AMOUNT | sed 's/MiB//g' | awk '{printf "%f\n", ($9/$11)*100 }' | awk '{ total += $1 } END {  if (NR > 0) print total/NR }')
  else
    # nvidia-smi is a bit slow, so simulate a pause here
    sleep 5
  fi

  #SYSTEM-WIDE
  MEM_USAGE=$(free -t | awk 'FNR == 2 {print ($3/$2)*100}')
  CPU_USAGE=$(top -b -n 2 -d 0.5 | fgrep "Cpu(s)" | tail -1 | gawk '{print $2+$4+$6}')
  CPU_USAGE_2=$(cat <(grep 'cpu ' /proc/stat) <(sleep 0.5 && grep 'cpu ' /proc/stat) | awk -v RS="" '{print ($13-$2+$15-$4)*100/($13-$2+$15-$4+$16-$5)}')


  # cactus-consolidated
  if [[ -z $consolidated_pid ]]; then
    consolidated_pid=$(ps axf | grep 'cactus_consolidated' | grep -v grep | awk '{print $1}') 
  fi

  #ps -o user,pid,ppid,ni,rss,sz,vsz,%cpu,%mem,state,pagein,etime,cmd --width=2048 >> ${CSV_FILE_2}
  #CPU_CONSOLIDATED=$(cat ${CSV_FILE_2} | grep cactus_consolidated | awk 'END {print $8}')
  #MEMORY_CONSOLIDATED=$(cat ${CSV_FILE_2} | grep cactus_consolidated | awk 'END {print $9}')

  elapsed=$(get_elapsed_time $start_time)
  format_time=$(TZ=UTC0 printf '%(%H:%M:%S)T\n' "$elapsed")

  if [[ "$GPU" == "YES" ]]; then

    echo "$elapsed,$format_time,$CPU_USAGE,$CPU_USAGE_2,$GPU_USAGE,$MEM_USAGE,$GPU_MEM_USAGE" >> $CSV_FILE
    rm $NVIDIA_LOG

  else
    if [[ -z $consolidated_pid ]]; then
      CPU_CONSOLIDATED=0.0
      MEMORY_CONSOLIDATED=0.0
    else
      top_consolidated=$(top -b -n 2 -d 0.2 -p $consolidated_pid | tail -1 )
      CPU_CONSOLIDATED=$(echo $top_consolidated | awk '{print $9}' )
      MEMORY_CONSOLIDATED=$(echo $top_consolidated | awk '{print $10}' )
      ps -p $consolidated_pid > /dev/null || unset consolidated_pid
    fi
    echo "$elapsed,$format_time,$CPU_USAGE,$CPU_USAGE_2,$MEM_USAGE,$CPU_CONSOLIDATED,$MEMORY_CONSOLIDATED" >> $CSV_FILE
  fi

  # if cactus process is dead, exit the script
  ps -p $cactus_pid > /dev/null || break

  sleep 0.5
done

echo "$(basename $0) finalised"
exit 0
