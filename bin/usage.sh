#!/bin/bash

function print_help() {
  echo "$(
    cat <<EOF
Usage:  bash $(basename $0) [option]
Options:
  -o | --output: output CVS-format filename
  -t | --TARGET: command-line to be listened; e.g., " -t cactus-preprocess\|cactus-blast\|cactus-align\|run_segalign"
  -g | --gpu: to parse resource usage outputeed from nvidia-smi
  -v | --verbose: verbosely mode
  -h | --help: to print this message
EOF
  )"
}

function get_elapsed_time() {
  echo "$SECONDS - $1" | bc -l
}

function get_target_process_pid() {

  start_time=$SECONDS
  target_proc_name=$1

  while true; do
    target_pid=$(pgrep --oldest --full "$target_proc_name")

    # if found it, job done
    if [[ "$target_pid" != "" ]]; then
      break
    fi
    sleep 1

    # waiting upon a deadline of 30 seconds
    elapsed=$(get_elapsed_time $start_time)
    if [[ "$elapsed" -gt "30" ]]; then
      echo "PID not found for $1, exiting with code 1"
      exit 1
    fi
  done

  echo "$target_pid"
}

# function get_all_children_pids() {
#   # Print all descendant pids of process pid $1
#   # adapted from https://unix.stackexchange.com/a/339071
#   process=${1:-1}
#   local children=()
#   while [ "$process" ]; do
#     children+=("$process")
#     unset tmp child
#     for p in $process; do
#       read -r child </proc/"$p"/task/"$p"/children 2>/dev/null
#       tmp="$tmp $child"
#     done
#     process=$tmp
#   done
#   echo "${children[@]}" | tr ' ' '\n' | sed '/^[[:space:]]*$/d' | tail -n +2
# }

function get_leaves_children() {

  # Print all descendant pids of process pid $1
  # adapted from https://unix.stackexchange.com/a/339071

  process=${1:-1}
  local leaves=()

  while [ "$process" ]; do
    unset tmp children
    for p in $process; do
      IFS=" " read -r -a children <<<"$(cat /proc/"$p"/task/"$p"/children 2>/dev/null)"
      if [ "${#children[@]}" == "0" ]; then
        leaves+=("$p")
      fi
      tmp="$tmp ${children[*]}"
    done
    process=("${tmp[@]}")
  done
  echo "${leaves[@]}" | tr ' ' '\n'
}

function get_comms() {
  # the given PID represented by $2 MUST be a child process of the process represented by the PID given by $1
  target_pid=$1
  current_pid=$2

  # list of commands from the given PID=$1 until its parent process (which PID=$TARGET_PID)
  local comms=()

  while true; do

    # <defunct>: some child process may have died already
    IFS=" " read -r -a array <<<"$(ps -o comm,ppid -p "$current_pid" --no-headers | sed 's/<defunct>//g')"

    # check the current command spiking the CPU usage
    child_comm="${array[0]}"

    # if we achieve the topiest pid we want; therefore leave the loop
    if [[ "$current_pid" == "$target_pid" ]]; then
      break
    fi

    # sanity-check: This is not suppose to happen
    if [[ "$current_pid" == "1" ]]; then
      echo >&2 "TARGET_PID=$target_pid is dead and it wasn't supposed to be happening! Exiting with code 1"
      exit 1
    fi

    # store the command to the array
    comms+=("$child_comm")

    # otherwise, update the parent PID and keeping going up
    current_pid="${array[1]}"

  done

  echo "${comms[@]}"
}

function grab_stats() {

  local root_pid=$1
  local gpu=$2
  local cvs_file=$3

  #preamble: header of the CVS-format file
  echo "TIME_SECONDS,TIME_FORMAT,CPU_USAGE_TOP,CPU_USAGE_PROC,MEM_USAGE,GPU_USAGE,GPU_MEM_USAGE" >>$cvs_file

  while true; do

    # gpu resource usage is 0.0 by default
    gpu_usage=0.0
    gpu_mem_usage=0.0

    # 1) GPU parser is slower, so try it first than grabbing CPU and Memory usage
    if [[ "$gpu" == "YES" ]]; then

      #nvidia filename
      nvidia_log_tmp_file="$(basedir $cvs_file)/nvidia-$(hostname).log"

      # remove previous rubbish if exists
      [ -f $nvidia_log_tmp_file ] && rm $nvidia_log_tmp_file
      nvidia-smi >$nvidia_log_tmp_file

      # give a pause to wait all the content be flushed to the file
      sleep 2

      # parse the data
      gpu_quantity=$(nvidia-smi --query-gpu=name --format=csv,noheader | wc -l)
      gpu_usage=$(grep "%" $nvidia_log_tmp_file | awk '{print $13}' | cut -d'%' -f1 | awk '{ sum += $1 } END {  if (NR > 0) print(sum / NR) }')
      gpu_mem_usage=$(grep "MiB" $nvidia_log_tmp_file | head -$gpu_quantity | sed 's/MiB//g' | awk '{printf "%f\n", ($9/$11)*100 }' | awk '{ total += $1 } END {  if (NR > 0) print total/NR }')

      # delete the file
      rm $nvidia_log_tmp_file
    fi

    # 2) Get CPU and memory SYSTEM-WIDE usage
    mem_ram_usage=$(free -t | awk 'FNR == 2 {print ($3/$2)*100}')
    cpu_usage_top=$(top -b -n 2 -d 0.5 | fgrep "Cpu(s)" | tail -1 | gawk '{print $2+$4+$6}')
    cpu_usage_proc=$(cat <(grep 'cpu ' /proc/stat) <(sleep 0.5 && grep 'cpu ' /proc/stat) | awk -v RS="" '{print ($13-$2+$15-$4)*100/($13-$2+$15-$4+$16-$5)}')

    # 3) get the commands (children process of the $root_pid) that are using CPU > 10%
    
    # create a tmp file to have a screenshot
    temp_file=$(mktemp)

    #xargs -n 1 -I{} ps -o pid,pcpu,comm --no-headers -p {} | awk -F " " '{ if ( $2 >=5 ) print $0 }' | awk '{A[$3]+=$2;I[$3]++}END{for(i in A) if (A[i]) printf "[%s %.2f%% %i]", i,A[i]/I[i],I[i]}'
    # delete the tmp file
    rm ${temp_file}

    # store data
    echo "$elapsed,$format_time,$cpu_usage_top,$cpu_usage_proc,$mem_ram_usage,$gpu_usage,$gpu_mem_usage" >>$cvs_file

    # watch $TARGET_PID to check it out if it is dead to break the loop
    ps -p $TARGET_PID >/dev/null || break

    # otherwise, $TARGET_PID still alive and grabs the resource usage for the next round of 20 seconds of waiting
    sleep 20

  done
}

function main() {

  # no argument given
  if [[ $#0 -eq 0 ]]; then
    print_help
    exit 1
  fi

  # parsing given arguments
  while [[ $# -gt 0 ]]; do

    key="$1"

    case $key in

    -o | --output)
      OUTPUT_CVS_FILE="$2"
      shift # past argument
      shift # past value
      ;;
    -h | --help)
      print_help
      exit 0
      ;;
    -g | --gpu)
      GPU=YES
      shift # past argument
      ;;
    -v | --verbose)
      VERBOSE=YES
      shift # past argument
      ;;
    -t | --target)
      TARGET="$2"
      shift # past argument
      shift # past value
      ;;
    *)                # unknown option
      UNKNOWN+=("$1") # save it in an array for later
      shift           # past argument
      ;;
    esac
  done
  set -- "${UNKNOWN[@]}" # restore UNKNOWN parameters

  if [[ "${#UNKNOWN[@]}" -gt 0 ]]; then
    echo "Unknown arguments      = ${UNKNOWN[@]}"
    echo "Run \"bash $(basename $0) --help\" for more option details"
    exit 1
  fi

  if [[ "$OUTPUT_CVS_FILE" == "" ]]; then
    echo "argument \"-o\" or \"--output\" is missing"
    exit 1
  fi

  if [[ "$VERBOSE" == "YES" ]]; then
    echo "Given arguments:"
    echo "  -o  = ${OUTPUT_CVS_FILE}"
    [[ "$GPU" == "YES" ]] && echo "  -g  = ${GPU}"
    echo "  -v  = ${VERBOSE}"
    echo "  -l  = ${TARGET}"
  fi

  # get PID of the target process
  TARGET_PID=$(get_target_process_pid $TARGET)

  if [[ "$VERBOSE" == "YES" ]]; then
    echo "PID=$TARGET_PID"
    echo "NAME=$(ps -p $TARGET_PID -o comm=)"
  fi

  # reset the clock
  start_time=$SECONDS

  # create resource profile
  grab_stats "$TARGET_PID" "$GPU" "$OUTPUT_CVS_FILE"

  [[ "$VERBOSE" == "YES" ]] && echo "$(basename $0) finalised"
}

# let's rock!!!
main "$@"

# mission accomplished =)
exit 0
