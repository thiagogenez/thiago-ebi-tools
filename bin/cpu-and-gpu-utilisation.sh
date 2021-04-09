#!/bin/bash

if [[ $# != 1 ]]; then
	echo "Wrong number of arguments. Usage: $(basename $0) </path/to/output/filename>"
	exit 0
fi

CSV_FILE=$1

#start_time="$(date +%s.%N)"
start_time=$SECONDS

echo "TIME_SECONDS,TIME_FORMAT,CPU_USAGE,GPU_USAGE" >> $CSV_FILE

while true
do
	CPU_USAGE=$(cat <(grep 'cpu ' /proc/stat) <(sleep 0.05 && grep 'cpu ' /proc/stat) | awk -v RS="" '{print ($13-$2+$15-$4)*100/($13-$2+$15-$4+$16-$5)}')
	GPU_USAGE=$(nvidia-smi | grep "%" | awk '{print $13}' | cut -d'%' -f1  | awk '{ sum += $1 } END { print(sum / NR) }')

	#end_time="$(date +%s.%N)"
	end_time=$SECONDS
	elapsed=$( echo "$end_time - $start_time" | bc -l )
	format_time=$(TZ=UTC0 printf '%(%H:%M:%S)T\n' "$elapsed")
	echo "$elapsed,$format_time,$CPU_USAGE,$GPU_USAGE" >> $CSV_FILE
done


