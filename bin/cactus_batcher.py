#!/usr/bin/env python3

import argparse
import contextlib
import os, tempfile, stat
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


def read_file(filename, line_number=False):
    """Function to read a file

    Args:
        @filename: The name of the file to read
        @line_number: return the number along with the line
    """
    with open(filename, mode="r") as f:
        number = 0
        while True:
            line = f.readline()
            if not line:
                break
            if line_number:
                yield line, number
                number = number + 1
            else:
                yield line



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


def append(filename, line, mode="a"):
    """Append content to a file

    Args:
        @filename: the name of the file to append information
        @line: string to append in the file as a line
    """

    if line:
        with open(filename, mode) as f:
            if f.tell() > 0:
                f.write("\n")
            f.write(line.strip())


def mkdir(path):
    if Path(path).exists():
        shutil.rmtree(path)

    Path(path).mkdir(parents=True, exist_ok=True)


def parse(read_func, symlink_dirs, task_dir, task_name, stop_condition, extra_dirs, ext="txt"):
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

    # Preamble - create links needed to execute Cactus at @task_dir
    # For the alignment step, these links must be created inside of each round  directory - which is done inside of the while loop below
    if "alignments" not in task_name:
        create_symlinks(src_dirs=symlink_dirs, dest="{}/{}".format(task_dir, task_name))
         
        # create extra dirs at task_dir
        for i in extra_dirs.values():
            mkdir("{}/{}/{}".format(task_dir, task_name, i))
    
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
            # define the correct filenames to write the line
            input_names = re.search("--inputNames (.*?) --", line).group(1).replace(' ','_')
            bash_files['all'] = "{}/{}/{}/{}.{}".format(task_dir, task_name, extra_dirs['all'], command_key, ext)
            bash_files['individual'] = "{}/{}/{}/{}.{}".format(task_dir, task_name, extra_dirs['individual'], input_names, ext)

        elif "alignments" in task_name:
            
            # preamble - create a new round directory
            if line.startswith(STRING_TABLE["round"]):
                round_id = line.split()[-1]
                round_path = "{}/{}/{}".format(task_dir, task_name, round_id)
                
                # create extra dirs at task_dir 
                for i in extra_dirs.values():
                    mkdir("{}/{}".format(round_path, i))
                
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
            
            # update filenames to write the line
            bash_files['all'] = "{}/{}/{}.{}".format(round_path, extra_dirs['all'], anc_id, ext) 
            bash_files['individual'] = "{}/{}/{}-{}.{}".format(round_path, extra_dirs['individual'], anc_id, command_key, ext)
        
        # update filenames to write the line
        elif "merging":
            parentName = line.split()[3]
            rootName = line.split()[4]

            bash_files['all'] = "{}/{}/{}/{}.txt".format(task_dir, task_name, extra_dirs['all'], command_key)
            bash_files['individual'] = "{}/{}/{}/{}-{}.txt".format(task_dir, task_name, extra_dirs['individual'], parentName, rootName)

        # write the line in the correct files
        for i in bash_files.keys():
            append(filename=bash_files[i], line=line)

       

def get_slurm_submission(name, work_dir, log_dir, partition, gpus, cpus, commands, dependencies):
    # sbatch command line
    sbatch = ['sbatch', '--parsable']
    sbatch.append('-J {}'.format(name))
    sbatch.append('-D {}'.format(work_dir))
    sbatch.append('-o {}/{}-%J.out'.format(log_dir, name))
    sbatch.append('-e {}/{}-%J.err'.format(log_dir, name))
    sbatch.append('-p {}'.format(partition))
   
    if gpus is not None or gpus == 0:
        sbatch.append('--gres=gpu:{}'.format(gpus))

    if cpus is not None:
        sbatch.append('-c {}'.format(cpus))

    if dependencies is not None and len(dependencies) > 0:
        sbatch.append('--dependency=afterok:${}'.format(',$'.join(dependencies)))
   
    sbatch.append('--wrap \"{}\"'.format(';'.join(commands)))

    return sbatch 


def make_executable(path):
    st = os.stat(path)
    os.chmod(path, st.st_mode | stat.S_IEXEC)


def slurmify(task_dir, task_name, extra_dirs, resources, ext='txt'):

    if "alignments" in task_name:
        rounds_dir = next(os.walk('{}/{}'.format(task_dir, task_name)), (None, None, []))[1]
        dirs = list(map(lambda e: '{}/{}'.format(extra_dirs['all'],e), rounds_dir))
        dirs.extend(list(map(lambda e: '{}/{}'.format(extra_dirs['individual'],e), rounds_dir)))
    else:
        dirs = [ 
            extra_dirs['all'],
            extra_dirs['individual']
        ]
    print(dirs)
    for root_dir in dirs:    
    
        # get list of filenames
        filenames = next(os.walk('{}/{}/{}'.format(task_dir, task_name, root_dir)), (None, None, []))[2]
            
        for filename in filenames: 
                   
            bash_filename, file_extension = os.path.splitext(filename)
                    
            # sanity check
            if ext not in file_extension:
                continue

            # create bash filename
            bash_filename = '{}/{}/{}/{}.sh'.format(task_dir, task_name, root_dir, bash_filename)
                   
            # add shebang
            append(filename=bash_filename, mode="w", line="#!/bin/bash")
                    
            # chmod +x on the bash script
            make_executable(path=bash_filename) 
                    
            # dependency slurm variable
            dependency_id = []
                    
            for line, line_number in read_file(filename='{}/{}/{}/{}'.format(task_dir, task_name, root_dir, filename), line_number=True):
                # get the cactus command
                command_key = line.split()[0] 
                        
                # remove rubbish 
                line = line.strip()
 
                # set Cactus log for Toil
                if command_key != 'halAppendSubtree':
                    line = line + ' --logFile {}/{}.txt'.format(extra_dirs['logs'], task_name) 
                                              
                        
                parameters = {
                     'name': '{}-{}'.format(task_name, line_number),
                     'work_dir': '{}/{}'.format(task_dir, task_name),
                     'log_dir': '{}'.format(extra_dirs['logs']),
                     'partition': '{}'.format(resources[command_key]['partition']),
                     'cpus': '{}'.format(resources[command_key]['cpus']),
                     'gpus': '{}'.format(resources[command_key]['gpus']),
                     'commands': ['{}'.format(line.strip())],
                     'dependencies': dependency_id 
                }
   
                # prepare slurm submission 
                sbatch = get_slurm_submission(**parameters)
                        
                # create dependencies between slurm calls
                if command_key == 'halAppendSubtree':
                    dependency_id.clear()
                    dependency_id.append('task_{}_{}'.format(re.sub('\W+|\d+','',task_name),line_number)) 
                    sbatch[0] = '{}=$(sbatch'.format(','.join(dependency_id))
                    sbatch.append(')')

                         
                        
                append(filename=bash_filename, line=' '.join(sbatch)) 
                        
                        


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

    resources = {
        'cactus-preprocess': {
            'cpus': 8,
            'gpus': 4,
            'partition': 'gpu96'                 
        },
        'halAppendSubtree':{
            'cpus': 1,
            'gpus': None,
            'partition': 'staff'
        }
    }

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
            task_name="1-preprocessors",
            task_dir=args.preprocessor_dir,
            stop_condition=STRING_TABLE["alignments"],
            extra_dirs=dict(logs="logs", all="sbatches/all", individual="sbatches/invididual")
        )

        parse(
            read_func=read_func,
            symlink_dirs=[args.steps_dir, args.jobstore_dir, args.input_dir],
            task_name="2-alignments",
            task_dir=args.alignments_dir,
            stop_condition=STRING_TABLE["merging"],
            extra_dirs=dict(logs="logs", all="sbatches/all", individual="sbatches/invididual")
        )

        parse(
            read_func=read_func,
            symlink_dirs=[args.steps_dir, args.jobstore_dir],
            task_name="3-merging",
            task_dir=args.merging_dir,
            stop_condition=None,
            extra_dirs=dict(logs="logs", all="sbatches/all", individual="sbatches/invididual")
        )

    # create slurm commands for cactus-preprocess
    slurmify(
        task_dir=args.preprocessor_dir, 
        task_name="1-preprocessors", 
        extra_dirs=dict(logs="logs", all="sbatches/all", individual="sbatches/invididual"), 
        resources=resources
    )

    # create slurm commands for merging
    slurmify(
        task_dir=args.alignments_dir, 
        task_name="2-alignments", 
        extra_dirs=dict(logs="logs", all="sbatches/all", individual="sbatches/invididual"), 
        resources=resources
    )

    # create slurm commands for merging
    slurmify(
        task_dir=args.merging_dir, 
        task_name="3-merging", 
        extra_dirs=dict(logs="logs", all="sbatches/all", individual="sbatches/invididual"), 
        resources=resources
    )



