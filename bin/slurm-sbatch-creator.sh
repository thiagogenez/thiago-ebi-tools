#!/bin/bash

#export TOIL_SLURM_ARGS="-p gpu96"

#####################
# PARSING ARGUMENTS
######################
EXEC=0
POSITIONAL=()
while [[ $# -gt 0 ]]; do

  key="$1"

  case $key in
    
    -i|--input)
      COMMANDS_FILE="$2"
      shift # past argument
      shift # past value
    ;;

    -e|--exe)
      EXEC=1
      shift
    ;;

    -h|--help)
      echo "$(cat <<EOF
Usage:  bash $(basename $0) [option]
Options:
  -i | --input: input command filename
  -h | --help: to print this message
  -e | --exe: call sbatch
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
  exit 1
fi


#####################
# RUN COMMAND
######################
call(){

	eval name="$1"
  	eval work_dir="$2"
	eval log_dir="$3"
  	eval partition="$4"
	eval gpus="$5"
	eval cpus="$6"
	eval cmd="$7"
	eval script_filename="$8"
	echo "$(cat <<EOF
#!/bin/bash
sbatch \
-J $name \
-D $work_dir \
-o $log_dir/$name.stdout \
-e $log_dir/$name.stderr \
-p $partition \
--gres=gpu:$gpus \
-c $cpus \
--wrap "$cmd"
EOF
)" > $script_filename

	chmod +x $script_filename
}


dir=$(dirname $(readlink -f "$COMMANDS_FILE"))


while IFS= read -r line || [ -n "$line" ];
do
	command=$(echo $line | grep  -o cactus-[a-z]* | head -1)
	
	#command-line
	cmd="singularity run --nv ~/cactus-gpu.img $line"

	
	if [[ "$(echo $command | cut -d'-' -f1)" == "cactus"  ]]; then
		
		if [[ "$command" == "cactus-preprocess" ]];then 
			name="preprocess-$(echo $line | awk -F "--inputNames " '{print $2}' | awk '{print $1}')"
			cpus=96
			gpus=4
			partition="gpu96"
		elif [[ "$command" == "cactus-blast" ]]; then 
			name="blast-$(echo $line | awk -F "--root " '{print $2}' | awk '{print $1}')"
			cpus=96
			gpus=4
			partition="gpu96"
		elif [[ "$command" == "cactus-align" ]]; then
			name="align-$(echo $line | awk -F "--root " '{print $2}' | awk '{print $1}')"
			cpus=96
			gpus=0
			partition="stan96"
		fi
		

		jb=$(echo $line | grep  -o "jobstore/[0-9]*" | cut -d'/' -f2)
		name="$jb-$name"

		if [ -d $dir/jobstore/$jb ]; then
			cmd="$cmd --restart"
		fi
	else
		name="hal2fasta-$(echo $line | awk '{print $3}')"
		cpus=10
		gpus=0
		partition="stan96,mem64"
	fi
	
	
	#variables
	log_dir=$dir/logs
	work_dir=$dir
	script_filename="$dir/sbatches/$name.sh"


	if [[ "$gpus" -gt 0  ]]; then
		cmd="/bin/bash $HOME/.gpu-wait.sh; $cmd"
	fi
	

	call "\${name}" "\${work_dir}" "\${log_dir}" "\${partition}" "\${gpus}" "\${cpus}" "\${cmd}" "\${script_filename}"
	
	if [[ "$EXEC" == "1" ]]; then
		/bin/bash $script_filename
	fi	

done < "$COMMANDS_FILE"
