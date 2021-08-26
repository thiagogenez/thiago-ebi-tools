#!/usr/bin/env python3

import argparse
import contextlib
import os, tempfile, stat
import shutil
import tempfile
import pathlib
import re
from pathlib import Path

try:
    import yaml
    from yaml.loader import SafeLoader
except ModuleNotFoundError as err:
    # Error handling
    print(err)
    print('Please, run "pip install PyYAML" to install PyYAML module')
    exit(1)

###################################################################
###                    UTILITY   FUNCTIONS                       ##
###################################################################


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
            raise IsADirectoryError(
                f"Cannot symlink over existing directory: '{link_name}'"
            )
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


def mkdir(path, force=False):
    """Create a directory

    Args:
        @path: path to create directories
        @force: if the directory exists, delete and recreate it

    """
    if force and Path(path).exists():
        shutil.rmtree(path)

    Path(path).mkdir(parents=True, exist_ok=True)


def make_executable(path):
    """Make a file executable, e.g., chmod +x

    Args:
        @path: path to a file
    """
    st = os.stat(path)
    os.chmod(path, st.st_mode | stat.S_IEXEC)


def create_bash_script(filename, shebang="#!/bin/bash"):
    """Create executable bash script with shebang on it

    Args:

        @filename: Path of the file
        @shebang: String containing bash shebang
    """
    append(filename=filename, mode="w", line=shebang)

    # chmod +x on it
    make_executable(path=filename)


def create_argparser():
    """Create argparser object to parse the input for this script"""

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--commands",
        metavar="PATH",
        type=str,
        required=True,
        help="File containing the command lines generated by the cactus-prepare",
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
        "--input_dir",
        metavar="PATH",
        type=str,
        required=True,
        help="Location of the input directory",
    )
    parser.add_argument(
        "--output_dir",
        metavar="PATH",
        type=str,
        required=True,
        help="Location of the output directory",
    )
    parser.add_argument(
        "--slurm",
        metavar="FILE",
        type=str,
        required=True,
        help="YAML file describing the SLURM resources",
    )
    return parser


def cactus_job_command_name(line):
    """Gathering information according to the cactus command line

    Args:
        @line: string containing a line read from the file

    Returns:
        a triple (command, extra_info, variable_name) informing:
        - command: a string showing the given command line (cactus-preprocess, cactus-blast, cactus-align, etc.)
        - extra_info: Info regarding the command line
        - variable_name: a unique value for the given command line
    """
    if isinstance(line, str) and len(line) > 0:
        command = line.split()[0]

        if "cactus" in command:
            jb = re.findall("\d+", line.split()[1])[0]
            if "preprocess" in command:
                input_names = (
                    re.search("--inputNames (.*?) --", line).group(1).replace(" ", "_")
                )
                variable_name = "{}_{}_{}".format(
                    command.replace("-", "_"), jb, input_names
                ).upper()
                return command, input_names, variable_name

            elif "blast" in command or "align" in command:
                anc_id = re.findall("--root (.*)$", line)[0].split()[0]
                variable_name = "{}_{}_{}".format(
                    command.replace("-", "_"), jb, anc_id
                ).upper()
                return command, anc_id, variable_name

        elif command == "hal2fasta":
            anc_id = re.findall("(.*) --hdf5InMemory", line)[0].split()[-1]
            variable_name = "{}_{}".format(command, anc_id).upper()
            return command, anc_id, variable_name

        elif command == "halAppendSubtree":
            parent_name = line.split()[3]
            root_name = line.split()[4]
            variable_name = "{}_{}_{}".format(command, parent_name, root_name).upper()
            return command, "{}_{}".format(parent_name, root_name), variable_name


def parse_yaml(filename):
    """YAML parser.

    Args:
        filename: Filename path

    Returns:
        YAML content or None otherwise
    """

    with open(filename, mode="r") as f: 
        return yaml.load(f, Loader=SafeLoader)

    return None

###################################################################
###               CACTUS-BATCHER  PARSING STEP                   ##
###################################################################


def parse(
    read_func,
    symlink_dirs,
    task_dir,
    task_name,
    task_type,
    stop_condition,
    essential_dirs,
    ext="dat",
):
    """Main function to parse the output file of Cactus-prepare

    Args:
        @read_func: pointer to the function that yields input lines
        @symlink_dirs: list of directories (as source) for symlink creation
        @task_dir: the directory to save parser's output
        @task_name: parser rule name (preprocessor, alignment, merging)
        @task_type: type of the given task
        @stop_condition: the condition to stop this parser
        @essential_dirs: list of extra directories to be created inside of @task_dir
    """

    # dict to point to parsed files
    parsed_files = {}

    # Preamble - create links needed to execute Cactus at @task_dir
    # For the alignment step, these links must be created inside of each round  directory - which is done inside of the while loop below
    if "alignments" != task_type:
        create_symlinks(src_dirs=symlink_dirs, dest="{}/{}".format(task_dir, task_name))

        # create extra dirs at task_dir
        for i in essential_dirs.values():
            mkdir("{}/{}/{}".format(task_dir, task_name, i), force=True)

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

        if "preprocessor" == task_type:
            # define the correct filenames to write the line
            _, input_names, _ = cactus_job_command_name(line)

            parsed_files["all"] = "{}/{}/{}/all-{}.{}".format(
                task_dir, task_name, essential_dirs["all"], task_type, ext
            )
            parsed_files["separated"] = "{}/{}/{}/{}.{}".format(
                task_dir, task_name, essential_dirs["separated"], input_names, ext
            )

        elif "alignments" == task_type:

            # preamble - create a new round directory
            if line.startswith("### Round"):
                round_id = line.split()[-1]
                round_path = "{}/{}/{}".format(task_dir, task_name, round_id)

                # create extra dirs at task_dir
                for i in essential_dirs.values():
                    mkdir("{}/{}".format(round_path, i), force=True)

                # create links needed for execution
                create_symlinks(src_dirs=symlink_dirs, dest=round_path)

                # go to the next line
                continue

            # sanity check
            assert "round_path" in locals()

            # get Anc_id from the current command-line
            command, anc_id, _ = cactus_job_command_name(line)

            # update filenames to write the line
            parsed_files["all"] = "{}/{}/{}.{}".format(
                round_path, essential_dirs["all"], anc_id, ext
            )
            parsed_files["separated"] = "{}/{}/{}-{}.{}".format(
                round_path, essential_dirs["separated"], anc_id, command, ext
            )

        # update filenames to write the line
        elif "merging" == task_type:

            # get parent and root node from the command line
            _, parent_root_name, _ = cactus_job_command_name(line)

            parsed_files["all"] = "{}/{}/{}/all-{}.{}".format(
                task_dir, task_name, essential_dirs["all"], task_type, ext
            )
            parsed_files["separated"] = "{}/{}/{}/{}.{}".format(
                task_dir,
                task_name,
                essential_dirs["separated"],
                parent_root_name,
                ext,
            )

        # write the line in the correct files
        for i in parsed_files.keys():
            append(filename=parsed_files[i], line=line)


###################################################################
###                  SLURM BASH SCRIPT CREATOR                   ##
###################################################################


def get_slurm_submission(
    job_name,
    variable_name,
    work_dir,
    log_dir,
    partition,
    gpus,
    cpus,
    commands,
    dependencies,
):

    """Prepare a Slurm string call

    Args:
        @name: name for the Slurm job
        @word_dir: Location where the slurm should to to run the command
        @log_dir: Path Cactus' log
        @partition: Slurm partition name to dispatch the job
        @gpus: Amount of GPUs to run the job
        @cpus: Amount of CPUs to run the job
        @commands: List of commands that the Slurm job must run
        @dependencies: list of Job IDs that this job depends on
    """

    # sbatch command line
    sbatch = ["TASK_{}=$(sbatch".format(variable_name), "--parsable"]
    sbatch.append("-J {}".format(job_name))

    if work_dir is not None:
        sbatch.append("-D {}".format(work_dir))

    sbatch.append("-o {}/{}-%j.out".format(log_dir, job_name))
    sbatch.append("-e {}/{}-%j.err".format(log_dir, job_name))
    sbatch.append("-p {}".format(partition))

    if gpus is not None:
        sbatch.append("--gres=gpu:{}".format(gpus))

    if cpus is not None:
        sbatch.append("-c {}".format(cpus))

    if dependencies is not None and len(dependencies) > 0:
        sbatch.append(
            "--dependency=afterok:${}".format(
                ",$".join(["TASK_" + dep for dep in dependencies])
            )
        )

    sbatch.append('--wrap "singularity run /apps/cactus/images/cactus.sif {}")'.format(";".join(commands)))

    return sbatch


def slurmify(
    task_dir,
    task_name,
    task_type,
    script_dir,
    log_dir,
    resources,
    initial_dependencies,
    ext="dat",
):
    """Wraps each command line into a Slurm job

    Args:
        @task_dir: Location of the cactus task
        @task_name: Name of the cactus task
        @task_type: type of the given task
        @script_dir: Directory to read data and create script
        @log_dir: Log path for Cactus call
        @resources: Slurm resources information
        @ext: Extension for the files that contains the command lines
    """

    # get list of filenames
    filenames = next(
        os.walk("{}/{}/{}".format(task_dir, task_name, script_dir)), (None, None, [])
    )[2]

    # list of variable names that serve as dependencies for the next batch
    extra_dependencies = []

    for filename in filenames:

        bash_filename, file_extension = os.path.splitext(filename)

        # sanity check
        if ext not in file_extension:
            continue

        # create bash filename
        bash_filename = "{}/{}/{}/{}.sh".format(
            task_dir, task_name, script_dir, bash_filename
        )
        create_bash_script(filename=bash_filename)

        # dependency slurm variable
        intra_dependencies = list(initial_dependencies)

        for line in read_file(
            filename="{}/{}/{}/{}".format(task_dir, task_name, script_dir, filename)
        ):
            # remove rubbish
            line = line.strip()

            # get the cactus command and variable name create that will serve as bash variable name and slurm job name
            command_key, job_name, variable_name = cactus_job_command_name(line)

            # set Cactus log file for Toil outputs
            if command_key != "halAppendSubtree" or command_key != "hal2fasta":
                line = line + " --logFile {}/{}/{}/{}-{}.log".format(task_dir, task_name, log_dir, command_key, job_name)

            # update the extra dependency between task types
            extra_dependencies.append(variable_name)
            if command_key == "cactus-blast" or command_key == "cactus-align":
                extra_dependencies.pop()

            # prepare slurm submission
            kwargs = {
                "job_name": '{}-{}'.format(command_key,job_name),
                "variable_name": variable_name,
                "work_dir": "{}/{}".format(task_dir, task_name),
                "log_dir": "{}/{}/{}".format(task_dir, task_name,log_dir),
                "partition": "{}".format(resources[command_key]["partition"]),
                "cpus": resources[command_key]["cpus"],
                "gpus": resources[command_key]["gpus"],
                "commands": ["{}".format(line.strip())],
                "dependencies": intra_dependencies,
            }

            # get the slurm string call
            sbatch = get_slurm_submission(**kwargs)

            # update the intra dependency list between command_key
            if (
                command_key == "halAppendSubtree"
                or command_key == "cactus-blast"
                or command_key == "cactus-align"
            ):
                intra_dependencies.clear()
                intra_dependencies.append(variable_name)

            # store it in the file bash script
            append(filename=bash_filename, line=" ".join(sbatch))

    # dependencies for the next batch
    return extra_dependencies


###################################################################
###          SLURM  WORKFLOW BASH SCRIPT CREATOR                 ##
###################################################################


def create_workflow_script(
    task_dir, task_name, task_type, script_dir, workflow_filename
):

    # adding preprocess
    append(filename=workflow_filename, line="\n### - {} step\n".format(task_type))

    # get path path for all-{}.sh bash script
    path = "{}/{}/{}".format(
        task_dir,
        task_name,
        script_dir,
    )
    filenames = next(os.walk(path), (None, None, []))[2]

    # check all files
    for filename in filenames:

        # update filename path
        script = "{}/{}".format(path, filename)

        # filtering files that aren't executable
        if os.path.isfile(script) and not os.access(script, os.X_OK):
            continue

        line = ["source", script]

        append(filename=workflow_filename, line=" ".join(line))


###################################################################
###                             MAIN                             ##
###################################################################

if __name__ == "__main__":

    ###################################################################
    ###                   PYTHON  ARGPARSE STEP                      ##
    ###################################################################

    # parse the args given
    args = create_argparser().parse_args()

    # get absolute path
    args.steps_dir = os.path.abspath(args.steps_dir)
    args.jobstore_dir = os.path.abspath(args.jobstore_dir)
    args.input_dir = os.path.abspath(args.input_dir)
    args.output_dir = os.path.abspath(args.output_dir)

    # get SLURM resources
    resources = parse_yaml(filename=args.slurm)

    # create pointer to the read function
    read_func = read_file(args.commands)

    ###################################################################
    ###                          DATA                                ##
    ###################################################################

    # essential data for parsing function
    data = {
        "trigger_parsing": "## Preprocessor",
        "task_order": ["preprocessor", "alignments", "merging"],
        "workflow_script_name": "run_cactus_workflow",
        "jobs": {
            "preprocessor": {
                "task_name": "1-preprocessors",
                "task_dir": args.output_dir,
                "stop_condition": "## Alignment",
                "symlink_dirs": [args.steps_dir, args.jobstore_dir, args.input_dir],
                "essential_dirs": [
                    {
                        "logs": "logs",
                        "all": "scripts/all",
                        "separated": "scripts/separated",
                    }
                ],
            },
            "alignments": {
                "task_name": "2-alignments",
                "task_dir": args.output_dir,
                "stop_condition": "## HAL merging",
                "symlink_dirs": [args.steps_dir, args.jobstore_dir, args.input_dir],
                "essential_dirs": [
                    {
                        "logs": "logs",
                        "all": "scripts/all",
                        "separated": "scripts/separated",
                    }
                ],
            },
            "merging": {
                "task_name": "3-merging",
                "task_dir": args.output_dir,
                "stop_condition": None,
                "symlink_dirs": [
                    args.steps_dir,
                    args.jobstore_dir,
                ],
                "essential_dirs": [
                    {
                        "logs": "logs",
                        "all": "scripts/all",
                        "separated": "scripts/separated",
                    }
                ],
            },
        },
    }

    ###################################################################
    ###               CACTUS-PREAPRE  PARSING STEP                   ##
    ###################################################################

    # Parsing loop
    while True:

        # get a line from the input file
        line = next(read_func, "")

        # parsing job done
        if not line:
            break

        # wait...
        if not line.startswith(data["trigger_parsing"]):
            continue

        # starting parsing procedure
        for job in data["task_order"]:
            parse(
                read_func=read_func,
                symlink_dirs=data["jobs"][job]["symlink_dirs"],
                task_dir=data["jobs"][job]["task_dir"],
                task_name=data["jobs"][job]["task_name"],
                task_type=job,
                stop_condition=data["jobs"][job]["stop_condition"],
                essential_dirs=data["jobs"][job]["essential_dirs"][0],
            )

    ###################################################################
    ###            UPDATE ALIGNMENT ESSENTIAL DIRECTORIES            ##
    ###################################################################

    # update alignment job information including "essential_dirs" for each round dir
    job = "alignments"

    # get rounds
    round_dirs = sorted(
        next(
            os.walk("{}/{}".format(data["jobs"][job]["task_dir"], data["jobs"][job]["task_name"])),
            (None, None, []),
        )[1]
    )

    # get original dictionary structure
    d = data["jobs"][job]["essential_dirs"][0]

    # make the update
    data["jobs"][job]["essential_dirs"] = list(
        {key: "{}/{}".format(round_id, d[key]) for key in d.keys()}
        for round_id in round_dirs
    )

    ###################################################################
    ###                  SLURM BASH SCRIPT CREATOR                   ##
    ###################################################################

    # list to carry dependencies between job types, e.g., preprocess, alignment, merging
    dependencies = []

    for job in data["task_order"]:
        for essential_dir in data["jobs"][job]["essential_dirs"]:
            for key in ["all", "separated"]:
                dependencies = slurmify(
                    task_dir=data["jobs"][job]["task_dir"],
                    task_name=data["jobs"][job]["task_name"],
                    task_type=job,
                    script_dir=essential_dir[key],
                    log_dir=essential_dir["logs"],
                    resources=resources,
                    initial_dependencies=dependencies,
                )

    ###################################################################
    ###          SLURM  WORKFLOW BASH SCRIPT CREATOR                 ##
    ###################################################################

    # create a new bash script file there
    workflow_scripts = "{}/{}.sh".format(args.output_dir, data["workflow_script_name"])
    create_bash_script(filename=workflow_scripts)

    for job in data["task_order"]:
        for script_dir in data["jobs"][job]["essential_dirs"]:
            create_workflow_script(
                task_dir=data["jobs"][job]["task_dir"],
                task_name=data["jobs"][job]["task_name"],
                task_type=job,
                script_dir=script_dir["all"],
                workflow_filename=workflow_scripts,
            )
