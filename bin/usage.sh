#!/bin/bash

function print_help() {
  cat <<EOF
Usage:  bash $(basename "$0") [option]
Options:
  -o | --output: output CVS-format filename
  -t | --TARGET: command-line to be listened; e.g., " -t cactus-preprocess\|cactus-blast\|cactus-align\|run_segalign"
  -g | --gpu: to parse resource usage outputeed from nvidia-smi
  -v | --verbose: verbosely mode
  -h | --help: to print this message
EOF
}

function get_elapsed_time() {
  echo "$SECONDS - $1" | bc -l
}

function get_target_process_pid() {

  start_time=$SECONDS
  target_proc_name=$1

  while true; do
    # set user ID to avoid "hijacking" activities from another user
    target_pid=$(pgrep --oldest --full "$target_proc_name" --uid "$(id -u)")

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

function get_newest_descendants() {

  # Print all descendant that are leaves pids of $1, including $1 itself
  # Adapted from https://unix.stackexchange.com/a/339071

  local process=${1:-1}
  local descendants=("$process")

  while [ "$process" ]; do
    unset tmp children
    for p in $process; do
      IFS=" " read -r -a children <<<"$(cat /proc/"$p"/task/"$p"/children 2>/dev/null)"
      if [ "${#children[@]}" == "0" ]; then
        descendants+=("$p")
      fi
      tmp="$tmp ${children[*]}"
    done
    process=("${tmp[@]}")
  done
  echo "${descendants[@]}" | tr ' ' '\n'
}

function get_commands() {
  # Print the commands path from $2 to $1
  # The given PID represented by $2 MUST be a child process of the process represented by the PID given by $1

  # sanity-check
  if [ "$#" -ne 2 ]; then
    return 1
  fi

  target_pid=$1
  current_pid=$2

  # list of commands from the given PID=$1 until its parent process (which PID=$TARGET_PID)
  commands=()

  # in case $current_pid is already dead
  start_time="$SECONDS"
  timeout=2

  while true; do

    # <defunct>: some child process may have died already, so remove it to avoid misleading interpretation
    IFS=" " read -r -a array <<<"$(ps -o comm,ppid,cmd -p "$current_pid" --no-headers  2>/dev/null  | sed 's/<defunct>//g' )"

    # check the current command that is consuming the CPU usage
    descendant_command="${array[0]}"

    # especial case when $descendant_command == "python3"
    # extract the python filename
    if [[ "$descendant_command" == "python3" ]] && [[ "${array[0]}" == "${array[2]}" ]] && [[ "${array[3]}" != "" ]]; then
      descendant_command="python3/$(awk -F '/' '{print $NF}' <<<"${array[3]}")"
    fi

    # store the command to the array
    if [[ "${#descendant_command}" -gt "0" ]]; then
      commands+=("$descendant_command")
    fi

    # sanity-check: This is not suppose to happen
    if [[ "$current_pid" == "1" ]]; then
      echo >&2 "TARGET_PID=$target_pid seems to be dead and it wasn't supposed to happening! Exiting with code 1"
      exit 1
    fi

    # WAY OUY?

    # YES > if we achieve the topiest pid we want; therefore leave the loop
    if [[ "$current_pid" == "$target_pid" ]]; then
      break
    fi

    # NO -> otherwise, update the parent PID and keeping going up
    current_pid="${array[1]}"

    # if dies in the process, leave this loop
    elapsed=$(get_elapsed_time "$start_time")
    if [[ "$elapsed" -gt $timeout ]]; then
      break
    fi    

  done

  # echo if not empty
  [ -z "${commands[*]}" ] || echo "${commands[@]}"
}

function join_data() {
  local cvs_file=$1

  mapfile -t files < <(ls "${cvs_file}"*)
  sorted_files=()

  # join requires that the files MUST be sorted in a lexicographic or lexicographical order
  # otherwise, it will complain
  for f in "${files[@]}"; do
    {
      # grab the header and print it untouched
      IFS= read -ra header
      echo "${header[@]}"
      # now process (sort) the rest of the input
      sort -t ',' -k 1b,1
    } <"$f" >"$f".sorted
    sorted_files+=("$f".sorted)
  done

  # join files
  base_file="$cvs_file".sorted
  for f in "${sorted_files[@]}"; do
    if [[ "$f" != "$base_file" ]]; then

      # join data using TIMESTAMP as join field
      LC_COLLATE=C join -e 0.0 -t, -j 1 -o auto --header -a1 "$base_file" "$f" >"$base_file".tmp

      # update join's FILE1 input file
      mv "$base_file".tmp "$base_file"

      # remove the .sorted file
      rm "$f"
    fi
  done

  # sort the final file in a numeric (cronological) order
  sort -t ',' -k1,1 -n "$base_file" >"$cvs_file".joined

  # remove the .sorted file
  rm "$base_file"
}

function grab_stats() {

  local oldest_pid=$1
  local gpu=$2
  local cvs_file=$3
  local start_time=$4

  #preamble: header of the CVS-format file
  echo "TIME_SECONDS,TIME_FORMAT,OVERALL_CPU_USAGE_TOP,OVERALL_CPU_USAGE_PROC,OVERALL_MEM_USAGE,OVERALL_GPU_USAGE,OVERALL_GPU_MEM_USAGE,OVERALL_NOTES" >>"$cvs_file"

  while true; do

    #######
    ### 1) GPU parser is slower, so try it first than grabbing CPU and Memory usage
    #######

    # gpu resource usage is 0.0 by default
    gpu_usage=0.0
    gpu_mem_usage=0.0

    if [[ "$gpu" == "YES" ]]; then

      #nvidia filename
      nvidia_log_tmp_file="$(basedir "$cvs_file")/nvidia-$(hostname).log"

      # remove previous rubbish if exists
      [ -f "$nvidia_log_tmp_file" ] && rm "$nvidia_log_tmp_file"
      nvidia-smi >"$nvidia_log_tmp_file"

      # give a pause to wait all the content be flushed to the file
      sleep 2

      # parse the data
      gpu_quantity=$(nvidia-smi --query-gpu=name --format=csv,noheader | wc -l)
      gpu_usage=$(grep "%" "$nvidia_log_tmp_file" | awk '{print $13}' | cut -d'%' -f1 | awk '{ sum += $1 } END {  if (NR > 0) print(sum / NR) }')
      gpu_mem_usage=$(grep "MiB" "$nvidia_log_tmp_file" | head -"$gpu_quantity" | sed 's/MiB//g' | awk '{printf "%f\n", ($9/$11)*100 }' | awk '{ total += $1 } END {  if (NR > 0) print total/NR }')

      # delete the file
      rm "$nvidia_log_tmp_file"
    fi

    #######
    ### 2) Get CPU and memory SYSTEM-WIDE usage
    #######
    mem_ram_usage=$(free -t | awk 'FNR == 2 {print ($3/$2)*100}')
    cpu_usage_top=$(top -b -n 2 -d 0.5 | grep -F "Cpu(s)" | tail -1 | gawk '{print $2+$4+$6}')
    cpu_usage_proc=$(cat <(grep 'cpu ' /proc/stat) <(sleep 0.5 && grep 'cpu ' /proc/stat) | awk -v RS="" '{print ($13-$2+$15-$4)*100/($13-$2+$15-$4+$16-$5)}')

    #######
    ### 3) Get the elepsed time
    #######
    elapsed=$(get_elapsed_time "$start_time")
    #format_time=$(TZ=UTC0 printf '%(%H:%M:%S)T\n' "$elapsed")
    format_time=$(bc <<<"$elapsed"/3600/24)$(date -ud "@$elapsed" +"d:%Hh:%Mm:%Ss")

    #######
    ### 4) get the commands (children process of the $oldest_pid) that are using CPU >= $cpu_threshold
    #######
    cpu_threshold=0.0

    # create a tmp file to have a screenshot of running process
    temp_file=$(mktemp)

    # get PID,PCPU,COMM for each running child process of $oldest_pid that is a leave (including the "root" oldest ancestor ifself )
    # <defunct>: some child process may have died already, so remove it to avoid misleading interpretation
    xargs -a <(get_newest_descendants "$oldest_pid") -n 1 -I{} ps -o pid,pcpu,pmem,comm --no-headers -p {} 2>/dev/null  |  grep -v "<defunct>" | awk  -v cpu_threshold="$cpu_threshold" -F " " \
      ' \
        { \
          if ( $2 >= cpu_threshold ) \
            print $0  \
        } \
      ' |
      sort -k4,4 >"$temp_file"

    # summarise children processes in the following format [PROCESS_NAME PROCESS_QUANTITY AVG_%_USAGE_ALLOCATED_CPU AVG_%_USAGE_MACHINE AVG_%_MEMORY_USAGE]
    unset individual_cpu_usage_per_process_type
    individual_cpu_usage_per_process_type=$(awk -v nproc="$(nproc)" \
      '\
        { \
          CPU[$4]+=$2; \
          MEM[$4]+=$3; \
          PS[$4]++; \
        } \
        END { \
          for(i in PS) \
            if (PS[i]) \
              printf "%s %i %.3f %.3f %.3f %.3f %.3f,", i, PS[i], CPU[i], CPU[i]/PS[i], (PS[i]/nproc)*(CPU[i]/PS[i]), MEM[i], MEM[i]/PS[i] \
        } \
      ' \
      "$temp_file")
    # remove the last char that is a comma ","
    individual_cpu_usage_per_process_type="${individual_cpu_usage_per_process_type%?}"

    # parse the resource usage for each command in a separated file
    unset rows
    IFS=, read -ra rows <<<"$individual_cpu_usage_per_process_type"
    for row in "${rows[@]}"; do
      unset values
      read -ra values <<<"${row}"
      outfile="$cvs_file"."${values[0]}"
      # write the header
      [ -f "$outfile" ] || echo "TIME_SECONDS,${values[0]}_TOTAL_CPU_USAGE,${values[0]}_ABSOLUTE_CPU_USAGE,${values[0]}_RELATIVE_CPU_USAGE,${values[0]}_TOTAL_MEM_USAGE,${values[0]}_RELATIVE_MEM_USAGE" >"$outfile"
      echo "$elapsed ${values[*]:1}" | tr ' ' ',' >>"$outfile"
    done

    # for each children process, get the path of commands between itself and its ascendent that the PID $oldest_pid
    unset descendant_path
    unset newest_descendant
    while read -r line; do
      # set user ID to avoid "hijacking" activities from another user 
      newest_descendant=$(pgrep --newest "$line" --uid "$(id -u)")
      descendant_path+=("$(get_commands "$oldest_pid" "$newest_descendant")")
    done < <(awk '{ PS[$4]++ } END { for (b in PS) { print b } }' "$temp_file")

    # organising the data as follows: [COMMAND_1>COMMAND_2>COMMAND_3>],
    descendant_path=("$(printf '[%s],' "${descendant_path[@]}" | tr ' ' '>')")
    # remove the last char that is a comma ","
    descendant_path=("${descendant_path%?}")

    # delete the tmp file
    rm "$temp_file"

    #######
    ### 5) Store data
    #######
    echo "$elapsed,$format_time,$cpu_usage_top,$cpu_usage_proc,$mem_ram_usage,$gpu_usage,$gpu_mem_usage,${descendant_path[*]}" >>"$cvs_file"

    #######
    ### 6) WAY OUT?
    #######

    # YES -> watch $TARGET_PID to check it out if it is dead to break/exit the loop
    ps -p "$oldest_pid" >/dev/null || break

    # NO -> otherwise, $TARGET_PID still alive and grabs the resource usage for the next round of 20 seconds of waiting
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
      output_cvs_file="$2"
      shift # past argument
      shift # past value
      ;;
    -h | --help)
      print_help
      exit 0
      ;;
    -g | --gpu)
      has_gpu=YES
      shift # past argument
      ;;
    -v | --verbose)
      verbose_mode=YES
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
    echo "Unknown arguments      = ${UNKNOWN[*]}"
    echo "Run \"bash $(basename "$0") --help\" for more option details"
    exit 1
  fi

  if [[ "$output_cvs_file" == "" ]]; then
    echo "argument \"-o\" or \"--output\" is missing"
    exit 1
  fi

  if [[ "$verbose_mode" == "YES" ]]; then
    echo "Given arguments:"
    echo "  -o  = ${output_cvs_file}"
    [[ "$has_gpu" == "YES" ]] && echo "  -g  = ${has_gpu}"
    echo "  -v  = ${verbose_mode}"
    echo "  -t  = ${TARGET}"
  fi

  # get PID of the target process
  target_pid=$(get_target_process_pid "$TARGET")

  if [[ "$verbose_mode" == "YES" ]]; then
    echo "TARGET_PID=$target_pid"
    echo "TARGET_PROCESS_NAME=$(ps -p "$target_pid" -o comm=)"
  fi

  # reset the clock
  start_time=$SECONDS

  # create resource profile
  grab_stats "$target_pid" "$has_gpu" "$output_cvs_file" "$start_time"

  # merge stats into one file
  join_data "$output_cvs_file"

  [[ "$verbose_mode" == "YES" ]] && echo "$(basename "$0") finalised"
}
# let's rock!!!
main "$@"

# mission accomplished =)
exit 0
