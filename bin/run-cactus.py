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
    "preprocessor": "## Preprocessor",
}


def create_symlinks(src_dirs, dest):
    pathlib.Path(dest).mkdir(parents=True, exist_ok=True)

    for i in src_dirs:
        relativepath = os.path.relpath(i, dest)
        fromfolderWithFoldername = dest + "/" + os.path.basename(i)
        # print('dest={}, i={}, os.path.basename(i)={}'.format(dest, i, os.path.basename(i)))
        # print('fromfolderWithFoldername: '+fromfolderWithFoldername)
        # print('relativepath: '+ relativepath)
        # exit(0)
        os.symlink(src=relativepath, dst=fromfolderWithFoldername)


def append(filename, line):
    if line:
        with open(filename, mode="a") as f:
            if f.tell() > 0:
                f.write("\n")
            f.write(line.strip())


def parse(read_func, symlink_dirs, task_dir, task_name, stop_condition):

    if "alignment" not in task_name:
        path = "{}/{}".format(task_dir, task_name)
        create_symlinks(src_dirs=symlink_dirs, dest=path)
        commands_filename = "{}/commands.txt".format(path)

    while True:
        # get the next line
        line = next(read_func, None)

        # job done: NONE
        if not line:
            break

        # strip the line
        line = line.strip()

        # empty line, next
        if not line:
            continue

        # job done for task_name
        if stop_condition and line.startswith(stop_condition):
            break

        if "alignment" in task_name:
            # create a new round directory
            if line.startswith(STRING_TABLE["round"]):
                round_id = line.split()[-1]
                round_path = "{}/alignments/{}".format(task_dir, round_id)
                create_symlinks(src_dirs=symlink_dirs, dest=round_path)

                # go to the next line
                continue

            # sanity check
            assert "round_path" in locals()

            # get Anc_id from the current command-line
            anc_id = re.findall("Anc[0-9]+", line)[0]

            # create block filename
            commands_filename = "{}/{}.txt".format(round_path, anc_id)

        # write the current command-line in the file
        append(filename=commands_filename, line=line)


def read_file(filename):
    with open(filename, mode="r") as f:
        while True:
            line = f.readline()
            if not line:
                break
            yield line


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
        "--alignments_dir",
        metavar="PATH",
        type=str,
        default=os.getcwd(),
        required=False,
        help="Location of the aligment directory",
    )
    parser.add_argument(
        "--preprocessor_dir",
        metavar="PATH",
        type=str,
        default=os.getcwd(),
        required=False,
        help="Location of the preprocessor directory",
    )
    parser.add_argument(
        "--merging_dir",
        metavar="PATH",
        type=str,
        default=os.getcwd(),
        required=False,
        help="Location of the merging directory",
    )
    parser.add_argument(
        "--input_dir",
        metavar="PATH",
        type=str,
        required=True,
        help="Location of the input directory",
    )
    args = parser.parse_args()

    args.alignments_dir = os.path.abspath(args.alignments_dir)
    args.steps_dir = os.path.abspath(args.steps_dir)
    args.jobstore_dir = os.path.abspath(args.jobstore_dir)
    args.input_dir = os.path.abspath(args.input_dir)
    args.preprocessor_dir = os.path.abspath(args.preprocessor_dir)
    args.merging_dir = os.path.abspath(args.merging_dir)

    read_func = read_file(args.commands)
    while True:
        line = next(read_func, "")
        if not line:
            break
        if not line.startswith(STRING_TABLE["preprocessor"]):
            continue

        parse(
            read_func=read_func,
            symlink_dirs=[args.steps_dir, args.jobstore_dir, args.input_dir],
            task_name="preprocessor",
            task_dir=args.preprocessor_dir,
            stop_condition=STRING_TABLE["alignment"],
        )

        parse(
            read_func=read_func,
            symlink_dirs=[args.steps_dir, args.jobstore_dir],
            task_name="alignment",
            task_dir=args.alignments_dir,
            stop_condition=STRING_TABLE["merging"],
        )

        parse(
            read_func=read_func,
            symlink_dirs=[args.steps_dir, args.jobstore_dir],
            task_name="merging",
            task_dir=args.merging_dir,
            stop_condition=None,
        )
