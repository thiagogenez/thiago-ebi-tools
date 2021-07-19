#!/usr/bin/env python3

import argparse
import contextlib
import os
import shutil
import tempfile
import pathlib
import re

STRING_TABLE = {
    "round": "### Round",
    "align": "cactus-align",
    "blast": "cactus-blast",
    "hal2fasta": "hal2fasta",
    "merging": "## HAL merging",
    "alignment": "## Alignment",
}


def prepare_round(steps_dir, jobstore_dir, round_path):
    pathlib.Path(round_path).mkdir(parents=True, exist_ok=True)

    for i in [steps_dir, jobstore_dir]:
        relativepath = os.path.relpath(i, round_path)
        fromfolderWithFoldername = round_path + '/' + os.path.basename(i)
        #print('round_path={}, i={}, os.path.basename(i)={}'.format(round_path, i, os.path.basename(i)))
        #print('fromfolderWithFoldername: '+fromfolderWithFoldername) 
        #print('relativepath: '+ relativepath)
        os.symlink(src=relativepath, dst=fromfolderWithFoldername)   
    

def append(filename, line):
    with open(filename, mode="a") as f:
        f.write(line + '\n')

def parse_preprocessor(lines, line_number, steps_dir, jobstore_dir, input_dir):

    while line_number < len(lines):
        line = lines[line_number].strip()
        
        # empty line, next
        if not line:
            # go to the next line
            line_number = line_number + 1
            continue

        # job done
        if line.startswith(STRING_TABLE["alignment"]):
            return line_number

    raise Exception("ERROR: parsing Preprocessor step")


def parse_alignment(lines, line_number, steps_dir, jobstore_dir, rounds_dir):

    while line_number < len(lines):
        line = lines[line_number].strip()
        
        # empty line, next
        if not line:
            # go to the next line
            line_number = line_number + 1
            continue

        # job done
        if line.startswith(STRING_TABLE["merging"]):
            return line_number

        # create a new round directory
        if line.startswith(STRING_TABLE["round"]):
            round_id = line.split()[-1]
            round_path = "{}/rounds/{}".format(rounds_dir, round_id)
            prepare_round(
                steps_dir=steps_dir,
                jobstore_dir=jobstore_dir,
                round_path=round_path,
            )

            block_id = 0
            
            # go to the next line
            line_number = line_number + 1
            continue

        # sanity check
        assert "round_path" in locals()

       	# get Anc_id from the current command-line
        anc_id = re.findall('Anc[0-9]+', line)[0]
        
        # create block filename
        block_filename = "{}/{}.txt".format(round_path, anc_id)

        # write the current command-line in the file
        append(filename=block_filename, line=line)

        # get the next line
        line_number = line_number + 1

    raise Exception("ERROR: Parsing alignment step")


if __name__ == "__main__":

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--commands",
        metavar="PATH",
        type=str,
        required=True,
        help="Output file from cactus-prepare command-line",
    )
    parser.add_argument(
        "--steps_dir",
        metavar="PATH",
        type=str,
        required=True,
        help="Location of the steps directory",
    )
    parser.add_argument(
        "--jobstore_dir",
        metavar="PATH",
        type=str,
        required=True,
        help="Location of the jobstore directory",
    )
    parser.add_argument(
        "--rounds_dir",
        metavar="PATH",
        type=str,
        default=None,
        required=False,
        help="Location of the rounds directory",
    )
    parser.add_argument(
        "--preprocess-only",
        metavar="True or False",
        type=bool,
        required=False,
        default=False,
        help="Prepare only cactus-preprocess command-line",
    )
    parser.add_argument(
        "--alignment-only",
        metavar="True or False",
        type=bool,
        required=False,
        default=False,
        help="Prepare only cactus-blast, cactus-align and command-lines",
    )

    args = parser.parse_args()

    with open(args.commands, mode="r") as f:
        lines = f.readlines()

        if args.rounds_dir is None:
            args.rounds_dir = os.path.dirname(os.path.realpath(f.name))
        else:
            args.rounds_dir = os.path.abspath(args.rounds_dir)

    args.steps_dir = os.path.abspath(args.steps_dir)
    args.jobstore_dir = os.path.abspath(args.jobstore_dir)

    line_number = 0
    while line_number < len(lines):
        line = lines[line_number].strip()
        if line.startswith(STRING_TABLE["round"]):
            line_number = parse_alignment(
                lines=lines,
                line_number=line_number,
                jobstore_dir=args.jobstore_dir,
                steps_dir=args.steps_dir,
                rounds_dir=args.rounds_dir,
            )
            
        line_number = line_number + 1
