#!/usr/bin/env python3

import argparse
import contextlib
import os, tempfile
import shutil
import tempfile
import pathlib
import re
from pathlib import Path

STRING_TABLE = {
    "round": "### Round",
    "align": "cactus-align",
    "blast": "cactus-blast",
    "hal2fasta": "hal2fasta",
    "merging": "## HAL merging",
    "alignments": "## Alignment",
    "preprocessors": "## Preprocessor",
}


def symlink(target, link_name, overwrite=False):
    """
    Create a symbolic link named link_name pointing to target.
    If link_name exists then FileExistsError is raised, unless overwrite=True.
    When trying to overwrite a directory, IsADirectoryError is raised.

    Credit: https://stackoverflow.com/a/55742015/825924
    """

    if not overwrite:
        os.symlink(target, link_name)
        return

    # os.replace() may fail if files are on different filesystems
    link_dir = os.path.dirname(link_name)

    # Create link to target with temporary filename
    while True:
        temp_link_name = tempfile.mktemp(dir=link_dir)

        # os.* functions mimic as closely as possible system functions
        # The POSIX symlink() returns EEXIST if link_name already exists
        # https://pubs.opengroup.org/onlinepubs/9699919799/functions/symlink.html
        try:
            os.symlink(target, temp_link_name)
            break
        except FileExistsError:
            pass

    # Replace link_name with temp_link_name
    try:
        # Pre-empt os.replace on a directory with a nicer message
        if not os.path.islink(link_name) and os.path.isdir(link_name):
            raise IsADirectoryError(f"Cannot symlink over existing directory: '{link_name}'")
        os.replace(temp_link_name, link_name)
    except:
        if os.path.islink(temp_link_name):
            os.remove(temp_link_name)
        raise


def create_symlinks(src_dirs, dest):
    """Create relative symbolic links

    Args:
        @src_dirs: list of source directory for symlink generation
        @dest: where the symlink must be created
    """
    pathlib.Path(dest).mkdir(parents=True, exist_ok=True)

    for i in src_dirs:
        relativepath = os.path.relpath(i, dest)
        fromfolderWithFoldername = dest + "/" + os.path.basename(i)
        symlink(target=relativepath, link_name=fromfolderWithFoldername, overwrite=True)


def append(filename, line):
    """Append content to a file

    Args:
        @filename: the name of the file to append information
        @line: string to append in the file as a line
    """

    if line:
        with open(filename, mode="a") as f:
            if f.tell() > 0:
                f.write("\n")
            f.write(line.strip())

def parse(read_func, symlink_dirs, task_dir, task_name, stop_condition, extra_dirs=dict(logs="logs", all="sbatches/all", individual="sbatches/invididual")):
    """Main function to parse the output file of Cactus-prepare

    Args:
        @read_func: pointer to the function that yields input lines
        @symlink_dirs: list of directories (as source) for symlink creation
        @task_dir: the directory to save parser's output
        @task_name: parser rule name (preprocessor, alignment, merging)
        @stop_condition: the condition to stop this parser
        @extra_dirs: list of extra directories to be created inside of @task_dir 
    """

    # dict to point to BASH files
    bash_files = {}
    
    # preamble - create links needed for execution at task_dir
    # for alignment step, these links must be created inside of each round  directory
    if "alignments" not in task_name:
        create_symlinks(src_dirs=symlink_dirs, dest="{}/{}".format(task_dir, task_name))
         
        # create extra dirs at task_dir
        for i in extra_dirs.values():
            Path("{}/{}/{}".format(task_dir, task_name, i)).mkdir(parents=True, exist_ok=True)
    else:
        extra_dirs['rounds'] = 'sbatches/rounds' 

    while True:
        # get the next line
        line = next(read_func, None)

        # job done: NONE
        if not line:
            break

        # strip the line
        line = line.strip()

        # empty line, get the next one ...
        if not line:
            continue

        # job done for task_name
        if stop_condition and line.startswith(stop_condition):
            break

        # get the cactus command
        command_key = line.split()[0]
        
        if "preprocessor" in task_name:
            jb_number = re.sub('\D', '', line.split()[1])

            # define the correcdt filenames to write the line
            bash_files['all'] = "{}/{}/{}/{}.sh".format(task_dir, task_name, extra_dirs['all'], command_key)
            bash_files['individual'] = "{}/{}/{}/{}-{}.sh".format(task_dir, task_name, extra_dirs['individual'], jb_number, command_key)

        elif "alignments" in task_name:
            
            # preamble - create a new round directory
            if line.startswith(STRING_TABLE["round"]):
                round_id = line.split()[-1]
                round_path = "{}/{}/{}".format(task_dir, task_name, round_id)
                
                # create extra dirs at task_dir 
                for i in extra_dirs.values():
                    Path("{}/{}".format(round_path, i)).mkdir(parents=True, exist_ok=True)
                
                # create links needed for execution
                create_symlinks(src_dirs=symlink_dirs, dest=round_path)

                # go to the next line
                continue

            # sanity check
            assert "round_path" in locals()

            # get Anc_id from the current command-line
            if "hal2fasta" in line:
                anc_id = re.findall("(.*) --hdf5InMemory", line)[0].split()[-1] 
            else:
                anc_id = re.findall("--root (.*)$", line)[0].split()[0] 
            
            # define the correct filenames to write the line
            bash_files['rounds'] = "{}/{}/{}.txt".format(round_path, extra_dirs['rounds'], anc_id) 
            bash_files['all'] = "{}/{}/{}.sh".format(round_path, extra_dirs['all'], command_key)
            bash_files['individual'] = "{}/{}/{}-{}.sh".format(round_path, extra_dirs['individual'], anc_id, command_key)

        elif "merging":
            bash_files['all'] = "{}/{}/{}/{}.sh".format(task_dir, task_name, extra_dirs['all'], command_key)

        for i in bash_files.keys():
            append(filename=bash_files[i], line=line)

        # write the current command-line in the file
        #append(filename=commands_filename, line=line)


def read_file(filename):
    """Function to read a file

    Args:
        @filename: The name of the file to read
    """
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
        help="Location of the alignment directory",
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

    # parse the args given
    args = parser.parse_args()
    args.alignments_dir = os.path.abspath(args.alignments_dir)
    args.steps_dir = os.path.abspath(args.steps_dir)
    args.jobstore_dir = os.path.abspath(args.jobstore_dir)
    args.input_dir = os.path.abspath(args.input_dir)
    args.preprocessor_dir = os.path.abspath(args.preprocessor_dir)
    args.merging_dir = os.path.abspath(args.merging_dir)

    # create pointer to the read function
    read_func = read_file(args.commands)

    # read the commands.txt file
    while True:
        line = next(read_func, "")
        if not line:
            break
        if not line.startswith(STRING_TABLE["preprocessors"]):
            continue

        parse(
            read_func=read_func,
            symlink_dirs=[args.steps_dir, args.jobstore_dir, args.input_dir],
            task_name="preprocessors",
            task_dir=args.preprocessor_dir,
            stop_condition=STRING_TABLE["alignments"],
        )

        parse(
            read_func=read_func,
            symlink_dirs=[args.steps_dir, args.jobstore_dir, args.input_dir],
            task_name="alignments",
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
