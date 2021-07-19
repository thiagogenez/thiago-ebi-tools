#!/usr/bin/env python3

import argparse
import contextlib
import os
import shutil
import tempfile
import pathlib

STRING_TABLE = {
    "round": "### Round",
    "align": "cactus-align",
    "blast": "cactus-blast",
    "hal2fasta": "hal2fasta",
    "merging": "## HAL merging",
}


def prepare_round(steps_dir, jobstore_dir, rounds_dir):
    pathlib.Path(rounds_dir).mkdir(parents=True, exist_ok=True)

    os.symlink(src=jobstore_dir, dst=rounds_dir, target_is_directory=True)
    os.symlink(src=steps_dir, dst=rounds_dir, target_is_directory=True)


def append(filename, line):
    with open(filename, mode="w+") as f:
        f.write(line)


def parse_alignment(lines, line_number, steps_dir, jobstore_dir, rounds_dir):

    while line_number < len(lines):
        line = lines[line_number].strip()

        if not line:
            continue

        if line.startswith(STRING_TABLE["merging"]):
            return line_number

        if line.startswith(STRING_TABLE["round"]):
            round_id = line.split()[-1]
            round_path = "{}/rounds/{}".format(rounds_dir, round_id)
            prepare_round(
                steps_dir=steps_dir,
                jobstore_dir=jobstore_dir,
                round_path=round_path,
            )

            block_id = 0
            continue

        assert "round_path" in locals()

        if line.startswith(STRING_TABLE["blast"]):
            block_filename = "{}/block-{}.txt".format(round_path, block_id)

        append(filename=block_filename, line=line)

        if line.startswith(STRING_TABLE["hal2fasta"]):
            block_id = block_id + 1

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
            line = parse_alignment(
                lines=lines,
                line_number=line_number,
                jobstore_dir=args.jobstore_dir,
                steps_dir=args.steps_dir,
                rounds_dir=args.rounds_dir,
            )

        line_number = line_number + 1
