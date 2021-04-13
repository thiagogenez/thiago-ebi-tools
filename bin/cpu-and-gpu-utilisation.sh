#!/bin/bash

if [[ $# != 1 ]]; then
	echo "Wrong number of arguments. Usage: $(basename $0) </path/to/output/filename>"
	exit 0
fi

CSV_FILE=$1

get_elapsed_time(){
	echo "$SECONDS - $1" | bc -l
}

start_time=$SECONDS
while true; do
	cactus_pid=$(ps axf | grep 'cactus-preprocess\|cactus-blast' | grep -v grep | awk '{print $1}')
	if [[ "$cactus_pid" != "" ]]; then
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

echo "TIME_SECONDS,TIME_FORMAT,CPU_USAGE,CPU_USAGE2,GPU_USAGE,MEM_USAGE" >> $CSV_FILE

while true; do
	# GPU parser is slower, so get it first
	GPU_USAGE=$(nvidia-smi | grep "%" | awk '{print $13}' | cut -d'%' -f1  | awk '{ sum += $1 } END { print(sum / NR) }')
	MEM_USAGE=$(free -t | awk 'FNR == 2 {print ($3/$2)*100}')
	CPU_USAGE=$(top -b -n2 -d 0.01 | fgrep "Cpu(s)" | tail -1 | gawk '{print $2+$4+$6}')
	CPU_USAGE_2=$(cat <(grep 'cpu ' /proc/stat) <(sleep 1 && grep 'cpu ' /proc/stat) | awk -v RS="" '{print ($13-$2+$15-$4)*100/($13-$2+$15-$4+$16-$5)}')
	
	
	elapsed=$(get_elapsed_time $start_time)
	format_time=$(TZ=UTC0 printf '%(%H:%M:%S)T\n' "$elapsed")
	
	echo "$elapsed,$format_time,$CPU_USAGE,$CPU_USAGE_2,$GPU_USAGE,$MEM_USAGE" >> $CSV_FILE

	# if cactus process is dead, exit the script
	ps -p $cactus_pid > /dev/null || break

	sleep 0.5
done

echo "$(basename $0) finalised"
exit 0


