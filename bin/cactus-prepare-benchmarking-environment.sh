#!/bin/bash

if [[ $# != 2 ]]; then
	echo "Wrong number of arguments. Usage: $(basename $0) /file/path/to/ specie-name"
	exit 1
fi

specie=$2
CONFIG_PATH=$1


if [[ ! -d $CONFIG_PATH/$specie ]]; then
	echo "No specie name at $CONFIG_PATH"
	exit 1
fi

PREPROCESS=(without-gpu with-gpu)
BLAST=(blast-without-gpu 25M 50M 100M 500M 1G 3G 6G)


cd $specie

# organising preprocess
[[ -d preprocess ]] && rm -rf preprocess
mkdir preprocess && cd preprocess

for preprocess in ${PREPROCESS[@]}; do
	[[ -d $preprocess ]] && rm -rf $preprocess

	# create the environment
	mkdir $preprocess && cd $preprocess
	ln -s ../../input .
	mkdir logs

	# create the calls
	cactus-prepare input/$specie-pairwise.processed.txt --outDir steps --outSeqFile steps/steps.txt --outHal steps/$specie-pairwise.hal --jobStore jobstore --preprocessBatchSize 1 --config $CONFIG_PATH/config-$preprocess.xml --cactusOptions '--realTimeLogging --logInfo --retryCount 0'  > orig-commands.txt

	# clean the calls
	cat orig-commands.txt  | grep cactus-preprocess > commands.txt
	cd ../

done
cd ../


# organising blast
[[ -d blast ]] && rm -rf blast
mkdir blast && cd blast

for preprocess in ${PREPROCESS[@]}; do

	preprocess="preprocess-$preprocess"

	# create the environment
        mkdir $preprocess && cd $preprocess

	for blast in ${BLAST[@]}; do

		# create the environment
		mkdir $blast && cd $blast
		ln -s ../../../input .
		mkdir logs

		# fix config xml filename
		config_filename="$CONFIG_PATH/config-gpu-$blast.xml"
		if [ "$blast" == "blast-without-gpu" ] ; then
			config_filename="$CONFIG_PATH/config-without-gpu.xml"
		fi

		# create the calls
		cactus-prepare input/$specie-pairwise.processed.txt --outDir steps --outSeqFile steps/steps.txt --outHal steps/$specie-preprocessing-$preprocess-and-$blast-blast.hal --jobStore jobstore --preprocessBatchSize 1 --config $config_filename --cactusOptions '--realTimeLogging --logInfo --retryCount 0' > orig-commands.txt

		# clean the calls
		cat orig-commands.txt  | grep cactus-blast > commands.txt
		cat orig-commands.txt  | grep cactus-align >> commands.txt
		cd ../
	done
	cd ../
done
cd ../