#!/bin/bash


#####################
# PARSING ARGUMENTS
######################
EXEC=0
POSITIONAL=()
while [[ $# -gt 0 ]]; do

  key="$1"

  case $key in

    -i|--input)
      DIR=$(dirname $(readlink -f "$2"))
      shift # past argument
      shift # past value
    ;;

    -s|--step)
      STEP="$2"
      shift # past argument
      shift # past value
    ;;

    -h|--help)
      echo "$(cat <<EOF
Usage:  bash $(basename $0) [option]
Options:
  -i | --input: input directory
  -h | --help: to print this message
  -s | --step: the step for Cactus run
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

# check unkown arguments
if [[ "${#UNKNOWN[@]}" -gt 0  ]]; then
  echo "Unknown arguments      = ${UNKNOWN[@]}"
  echo "Run \"bash $(basename $0) --help\" for more details"
  exit 1
fi

# sanity-check
if [[ "$STEP" != "preprocessor" ]] && [[ "$STEP" != "alignments" ]] && [[ "$STEP" != "merging" ]]; then
	echo -e "Unkown step = $STEP"
	echo "possible values: preprocessor, alignments, merging"
	exit 2
fi


call(){
	eval FILES="$1"
	eval SBATCHER="$2"

	for j in ${FILES[@]}; do
		file=$(readlink -f "$j")
		echo -e "\t---> calling $j"
		bash $SBATCHER -i $file -e
		sleep 20
		while [ "$(squeue --noheader)" != "" ]; do
			sleep 30
		done	
	done
}


#####################
# ELAPSED FUNCTION
######################
get_elapsed_time(){
	echo "$SECONDS - $1" | bc -l
}



run(){
	eval dir="$1"
	eval files="$2"

	# entering ...
	pushd $dir
	
	start_time=$SECONDS
	
	for file in ${FILES[@]}; do
		start_time_file=$SECONDS
		
		# call sbatch script
		bash /home/thiagogenez_ebi_ac_uk/git/thiago-ebi-tools/bin/slurm-sbatch-creator.sh -i $file -e
		sleep 10
		
		# wait until all jobs done
		while [ "$(squeue --noheader)" != "" ]; do
			sleep 30
		done

		# calculate runtine
		elapsed=$(get_elapsed_time $start_time_file)
		echo -e "\t $elapsed seconds for file $file"
	done

	# calculate overall runtime
	elapsed=$(get_elapsed_time $start_time)
	echo "$elapsed seconds for file $file"
	
	# leaving ...
	popd
}

main(){
	eval location="$1"
	eval step="$2"

	if [[ "$step" == "alignments" ]]; then
		
		files=("all-blast.txt" "all-align.txt" "all-hal2fasta.txt")
	else
		dirs=($location)
		files=("commands.txt")
	fi 

	for dir in ${dirs[@]}; do
		
	done	
}

pushd $DIR

for i in `seq $FROM $TO`; do
	pushd $i
	mkdir -p logs sbatches
	
	echo "running: $i"	
	for j in all-blast.txt all-align.txt all_hal2fasta.txt; do
		echo "---> calling $j"
		bash ../../../script.sh -i $j -e
		sleep 20
		while [ "$(squeue --noheader)" != "" ]; do
			sleep 30
		done	
	done
	popd
done
popd
