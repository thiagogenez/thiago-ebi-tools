#!/bin/bash

if [[ $# != 2 ]]; then
	echo "Wrong number of arguments. Usage: $(basename $0) /file/path/to/ specie-name"
	exit 1
fi

CONFIG_PATH=$1
specie=$2

# sanity check
if [[ ! -d $CONFIG_PATH/$specie ]]; then
	echo "No specie name $specie localised at $CONFIG_PATH/$specie"
	exit 1
fi

PREPROCESS=(without-gpu with-gpu)
BLAST=(blast-without-gpu 25M 50M 100M 500M 1G 3G 6G)
BLAST=(blast-without-gpu 50M 100M 500M 1G 3G 6G)

cd $specie

# sanity check
for dir in preprocess blast; do
	if [[ ! -d $dir ]]; then
		echo "No directory name $dir at $CONFIG_PATH/$specie"
		exit 1
	fi
done

for preprocess in ${PREPROCESS[@]}; do

	# GRAB FASTA FILES PATH
	cd preprocess/$preprocess
	# sanity check
	if [[ ! -d steps ]]; then
		echo "No directory name steps at $PWD"
		exit 1
	fi
	cd steps
	FASTA_FILES=$(ls $PWD/*.fa)
	cd ../../../

	# DEPLOY THE LINKS
	cd blast/preprocess-$preprocess

	for blast in ${BLAST[@]}; do

		# sanity check
		if [[ ! -d $blast/steps ]]; then
			echo "No directory name $blast/steps at $PWD"
			exit 1
		fi

		cd $blast/steps
			for fasta_file in ${FASTA_FILES[@]}; do
				ln -s $fasta_file .
			done
		cd ../../
	done

	cd ../../ 
done

cd ../
