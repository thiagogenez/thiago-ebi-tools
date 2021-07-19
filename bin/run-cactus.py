#!/usr/bin/env python3

import argparse
import contextlib
import os
import shutil
import tempfile
import pathlib

STRING_TABLE = {
	'round': '### Round',
	'align': 'cactus-align',
	'blast': 'cactus-blast'
	'hal2fasta': 'hal2fasta',
	'round_to_link': ['jobstore', 'steps'],
	'merging': '## HAL merging'
}


def prepare_round(dir, round_id, to_link):
	round_path = '{}/rounds/{}'.format(dir, round_id)
	pathlib.Path(round_path).mkdir(parents=True, exist_ok=True)

	for i in to_link:
		os.symlink(
			src='{}/{}'.format(dir, i), 
			dst='{}'.format(round_path),
			target_is_directory=True
		)
		
	return round_path

def append(filename, line):
	with open(filename, mode='w+') as f:
		f.write(line)

def parse_alignment(lines, dir, line_number):
		
	while line_number < len(lines):
		line = lines[line_number].strip()
		
		if not line:
			continue

		if line.startswith(STRING_TABLE['merging']):
			return line_number

		if line.startswith(STRING_TABLE['round']):
			round_id = line.split()[-1]	
			round_path = prepare_round(dir=dir, round_id=round_id, to_link=STRING_TABLE['round_to_link'])
			block_id = 0
			continue

		if line.startswith(STRING_TABLE['blast']):
			block_filename = '{}/block-{}.txt'.format(round_path, block_id)

		append(filename=block_filename, line=line)	

		if line.startswith(STRING_TABLE['hal2fasta']):
			block_id = block_id + 1

		line_number = line_number + 1

	raise Exception("ERROR: Parsing alignment step")

if __name__ == "__main__":

    parser = argparse.ArgumentParser()
    parser.add_argument('--command-file', metavar='PATH', type=str, required=True, help='Output file from cactus-prepare command-line')
    parser.add_argument('--dir', metavar='PATH',type=str, required=True, help='Directory that contains the step and jobstore directories')
    parser.add_argument('--preprocess-only', metavar='True or False', type=bool, required=False, default=False, help='Prepare only cactus-preprocess command-line')
    parser.add_argument('--alignment-only', metavar='True or False', type=bool, required=False, default=False, help='Prepare only cactus-blast, cactus-align and command-lines')


    args = parser.parse_args()