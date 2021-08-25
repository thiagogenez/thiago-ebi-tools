#!/usr/bin/env python3

import argparse
import contextlib
import os, tempfile, stat
import shutil
import tempfile
import pathlib
import re
from pathlib import Path


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
    return parser


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
            input_names = (
                re.search("--inputNames (.*?) --", line).group(1).replace(" ", "_")
            )
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
            if "hal2fasta" in line:
                anc_id = re.findall("(.*) --hdf5InMemory", line)[0].split()[-1]
            else:
                anc_id = re.findall("--root (.*)$", line)[0].split()[0]

            # update filenames to write the line
            parsed_files["all"] = "{}/{}/{}.{}".format(
                round_path, essential_dirs["all"], anc_id, ext
            )
            parsed_files["separated"] = "{}/{}/{}-{}.{}".format(
                round_path, essential_dirs["separated"], anc_id, line.split()[0], ext
            )

        # update filenames to write the line
        elif "merging" == task_type:

            parentName = line.split()[3]
            rootName = line.split()[4]

            parsed_files["all"] = "{}/{}/{}/all-{}.{}".format(
                task_dir, task_name, essential_dirs["all"], task_type, ext
            )
            parsed_files["separated"] = "{}/{}/{}/{}-{}.{}".format(
                task_dir,
                task_name,
                essential_dirs["separated"],
                parentName,
                rootName,
                ext,
            )

        # write the line in the correct files
        for i in parsed_files.keys():
            append(filename=parsed_files[i], line=line)


###################################################################
###                  SLURM BASH SCRIPT CREATOR                   ##
###################################################################


def get_slurm_submission(
    name, work_dir, log_dir, partition, gpus, cpus, commands, dependencies
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
    sbatch = ["task_{}=$(sbatch".format(name), "--parsable"]
    sbatch.append("-J {}".format(name))

    if work_dir is not None:
        sbatch.append("-D {}".format(work_dir))

    sbatch.append("-o {}/{}-%j.out".format(log_dir, name))
    sbatch.append("-e {}/{}-%j.err".format(log_dir, name))
    sbatch.append("-p {}".format(partition))

    if gpus is not None:
        sbatch.append("--gres=gpu:{}".format(gpus))

    if cpus is not None:
        sbatch.append("-c {}".format(cpus))

    if dependencies is not None and len(dependencies) > 0:
        sbatch.append(
            "--dependency=afterok:${}".format(
                ",$".join(["task_" + dep for dep in dependencies])
            )
        )

    sbatch.append('--wrap "{}")'.format(";".join(commands)))

    return sbatch


def slurmify(
    task_dir,
    task_name,
    task_type,
    essential_dirs,
    resources,
    initial_dependencies,
    ext="dat",
):
    """Wraps each command line into a Slurm job

    Args:
        @task_dir: Location of the cactus task
        @task_name: Name of the cactus task
        @task_type: type of the given task
        @essential_dirs: Essential directories where command lines are stored
        @resources: Slurm resources information
        @ext: Extension for the files that contains the command lines
    """
    dirs = [essential_dirs["all"], essential_dirs["separated"]]

    # if "alignments" == task_type:
    #    round_dirs = next(
    #        os.walk("{}/{}".format(task_dir, task_name)), (None, None, [])
    #    )[1]
    #    dirs = []

    # HACKY: a better solution definitely exists!
    #   for key in essential_dirs.keys():
    #       if "logs" not in key:
    #           dirs.extend(
    #               list(
    #                   map(
    #                       lambda e: "{}/{}".format(e, essential_dirs[key]), round_dirs
    #                   )
    #               )
    #           )

    # job id for slurm task name and bash variable purposes
    job_id = 0

    extra_dependencies = []
    for root_dir in dirs:

        # get list of filenames
        filenames = next(
            os.walk("{}/{}/{}".format(task_dir, task_name, root_dir)), (None, None, [])
        )[2]

        for filename in filenames:

            bash_filename, file_extension = os.path.splitext(filename)

            # sanity check
            if ext not in file_extension:
                continue

            # create bash filename
            bash_filename = "{}/{}/{}/{}.sh".format(
                task_dir, task_name, root_dir, bash_filename
            )
            create_bash_script(filename=bash_filename)

            # dependency slurm variable
            intra_dependencies = list(initial_dependencies)

            for line in read_file(
                filename="{}/{}/{}/{}".format(task_dir, task_name, root_dir, filename)
            ):
                # get the cactus command
                command_key = line.split()[0]

                # remove rubbish
                line = line.strip()

                # set Cactus log file for Toil outputs
                if command_key != "halAppendSubtree" or command_key != "hal2fasta":
                    line = line + " --logFile {}/{}.log".format(
                        essential_dirs["logs"], task_name
                    )

                job_name = "{}_{}".format(re.sub("\W+|\d+", "_", command_key), job_id)

                extra_dependencies.append(job_name)

                # prepare slurm submission
                kwargs = {
                    "name": job_name,
                    "work_dir": "{}/{}".format(task_dir, task_name),
                    "log_dir": "{}".format(essential_dirs["logs"]),
                    "partition": "{}".format(resources[command_key]["partition"]),
                    "cpus": resources[command_key]["cpus"],
                    "gpus": resources[command_key]["gpus"],
                    "commands": ["{}".format(line.strip())],
                    "dependencies": intra_dependencies,
                }
                sbatch = get_slurm_submission(**kwargs)

                # create dependencies between slurm calls
                if (
                    command_key == "halAppendSubtree"
                    or command_key == "cactus-blast"
                    or command_key == "cactus-align"
                ):
                    intra_dependencies.clear()
                    intra_dependencies.append(job_name)

                append(filename=bash_filename, line=" ".join(sbatch))

                # job_id ++
                job_id = job_id + 1

    # glue round calls in one bash script
    # if "alignments" == task_type:

    # create "log" and "script" directories for overall round directories
    #    for i in ["logs", "all"]:
    #       all_glued_scripts = "{}/{}/{}".format(
    #            task_dir, task_name, essential_dirs[i]
    #        )
    #        mkdir(path=all_glued_scripts, force=True)

    # create a new bash script file there
    #    all_glued_scripts = "{}/all-{}.sh".format(all_glued_scripts, task_type)
    #    create_bash_script(filename=all_glued_scripts)

    # sanity check for the local variable previously created
    #    assert "round_dirs" in locals()

    # dependency slurm variable
    #   dependency_id = []

    # check the bash scripts for each round
    #   for round_id in round_dirs:

    # get list of filenames
    #      path = "{}/{}/{}/{}".format(
    #          task_dir, task_name, round_id, essential_dirs["all"]
    #     )
    #     filenames = next(os.walk(path), (None, None, []))[2]

    # check all files
    #     for filename in filenames:

    # get ancestor id that is the filename itself
    #         anc_id = os.path.splitext(filename)[0]

    # update filename path
    #        ancestor_script = "{}/{}".format(path, filename)

    # filtering files that aren't executable
    #        if os.path.isfile(ancestor_script) and not os.access(
    #            ancestor_script, os.X_OK
    #        ):
    #            continue

    # prepare slurm submission
    #        kwargs = {
    #            "name": "{}-{}-{}".format(task_type, round_id, anc_id),
    #            "work_dir": None,
    #            "log_dir": "{}".format(essential_dirs["logs"]),
    #            "partition": "{}".format(resources["regular"]["partition"]),
    #            "cpus": resources["regular"]["cpus"],
    #            "gpus": resources["regular"]["gpus"],
    #            "commands": [ancestor_script],
    #            "dependencies": dependency_id,
    #        }
    #        sbatch = get_slurm_submission(**kwargs)

    # create dependencies between slurm calls
    #        dependency_id.clear()
    #        dependency_id.append("task_{}_{}".format(task_type,round_id))
    #        sbatch[0] = "{}=$(sbatch".format(",".join(dependency_id))
    #        sbatch.append(")")

    #       append(filename=all_glued_scripts, line=" ".join(sbatch))

    return extra_dependencies


###################################################################
###          SLURM  WORKFLOW BASH SCRIPT CREATOR                 ##
###################################################################


def create_workflow_script(
    workflow_dir, task_order, tasks, workflow_name="run-cactus-workflow"
):

    # create a new bash script file there
    workflow_scripts = "{}/{}.sh".format(workflow_dir, workflow_name)
    create_bash_script(filename=workflow_scripts)

    for task_type in task_order:

        # adding preprocess
        append(filename=workflow_scripts, line="\n### - {} step\n".format(task_type))

        # get path path for all-{}.sh bash script
        path = "{}/{}/{}".format(
            tasks[task_type]["task_dir"],
            tasks[task_type]["task_name"],
            tasks[task_type]["essential_dirs"]["all"],
        )
        filenames = next(os.walk(path), (None, None, []))[2]

        # check all files
        for filename in filenames:

            # update filename path
            script = "{}/{}".format(path, filename)

            # filtering files that aren't executable
            if os.path.isfile(script) and not os.access(script, os.X_OK):
                continue

            # dependency slurm variable
            dependency_id = []

            # prepare slurm submission
            kwargs = {
                "name": "all_{}".format(task_type),
                "work_dir": None,
                "log_dir": "{}".format(tasks[task_type]["essential_dirs"]["logs"]),
                "partition": "{}".format(resources["regular"]["partition"]),
                "cpus": resources["regular"]["cpus"],
                "gpus": resources["regular"]["gpus"],
                "commands": [script],
                "dependencies": dependency_id,
            }
            sbatch = get_slurm_submission(**kwargs)

            # create dependencies between slurm calls
            dependency_id.clear()
            dependency_id.append("task_all_{}".format(task_type))
            sbatch[0] = "{}=$(sbatch".format(",".join(dependency_id))
            sbatch.append(")")

            append(filename=workflow_scripts, line=" ".join(sbatch))


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

    # create pointer to the read function
    read_func = read_file(args.commands)

    ###################################################################
    ###               CACTUS-PREAPRE  PARSING STEP                   ##
    ###################################################################

    task_order = ["preprocessor", "alignments", "merging"]

    # essential data for parsing function
    parsing_data = {
        "trigger_parsing": "## Preprocessor",
        "jobs": {
            "preprocessor": {
                "task_name": "1-preprocessors",
                "task_dir": args.output_dir,
                "stop_condition": "## Alignment",
                "symlink_dirs": [args.steps_dir, args.jobstore_dir, args.input_dir],
                "essential_dirs": {
                    "logs": "logs",
                    "all": "scripts/all",
                    "separated": "scripts/separated",
                },
            },
            "alignments": {
                "task_name": "2-alignments",
                "task_dir": args.output_dir,
                "stop_condition": "## HAL merging",
                "symlink_dirs": [args.steps_dir, args.jobstore_dir, args.input_dir],
                "essential_dirs": {
                    "logs": "logs",
                    "all": "scripts/all",
                    "separated": "scripts/separated",
                },
            },
            "merging": {
                "task_name": "3-merging",
                "task_dir": args.output_dir,
                "stop_condition": None,
                "symlink_dirs": [
                    args.steps_dir,
                    args.jobstore_dir,
                ],
                "essential_dirs": {
                    "logs": "logs",
                    "all": "scripts/all",
                    "separated": "scripts/separated",
                },
            },
        },
    }

    # Parsing loop
    while True:

        # get a line from the input file
        line = next(read_func, "")

        # parsing job done
        if not line:
            break

        # wait...
        if not line.startswith(parsing_data["trigger_parsing"]):
            continue

        # starting parsing procedure
        for job in task_order:
            parse(
                **{
                    "read_func": read_func,
                    "task_type": job,
                    **parsing_data["jobs"][job],
                }
            )

    ###################################################################
    ###                  SLURM BASH SCRIPT CREATOR                   ##
    ###################################################################

    resources = {
        "cactus-preprocess": {"cpus": 8, "gpus": 4, "partition": "gpu96"},
        "cactus-blast": {"cpus": 8, "gpus": 4, "partition": "gpu96"},
        "cactus-align": {"cpus": 8, "gpus": 4, "partition": "gpu96"},
        "hal2fasta": {"cpus": 1, "gpus": None, "partition": "staff"},
        "halAppendSubtree": {"cpus": 1, "gpus": None, "partition": "staff"},
        "regular": {"cpus": 1, "gpus": None, "partition": "staff"},
    }

    slurm_data = {
        "preprocessor": {
            "task_name": parsing_data["jobs"]["preprocessor"]["task_name"],
            "task_dir": parsing_data["jobs"]["preprocessor"]["task_dir"],
            "essential_dirs": list(
                parsing_data["jobs"]["preprocessor"]["essential_dirs"]
            ),
            "resources": {"cactus-preprocess": resources["cactus-preprocess"]},
        },
        "alignments": {
            "task_name": parsing_data["jobs"]["alignments"]["task_name"],
            "task_dir": parsing_data["jobs"]["alignments"]["task_dir"],
            "essential_dirs": None,
            "resources": {
                "cactus-blast": resources["cactus-blast"],
                "cactus-align": resources["cactus-align"],
                "hal2fasta": resources["hal2fasta"],
                "regular": resources["regular"],
            },
        },
        "merging": {
            "task_name": parsing_data["jobs"]["merging"]["task_name"],
            "task_dir": parsing_data["jobs"]["merging"]["task_dir"],
            "essential_dirs": list(parsing_data["jobs"]["merging"]["essential_dirs"]),
            "resources": {"halAppendSubtree": resources["halAppendSubtree"]},
        },
    }

    # update alignment job information including "essential_dirs" for each round dir
    job = "alignments"

    # get rounds
    round_dirs = sorted(
        next(
            os.walk(
                "{}/{}".format(
                    slurm_data[job]["task_dir"], slurm_data[job]["task_name"]
                )
            ),
            (None, None, []),
        )[1]
    )

    # get original dictionary structure
    d = parsing_data["jobs"][job]["essential_dirs"]

    # make the update
    slurm_data[job]["essential_dirs"] = list(
        {key: "{}/{}".format(round_id, d[key]) for key in d.keys()}
        for round_id in round_dirs
    )

    # list to carry dependencies between job types, e.g., preprocess, alignment, merging
    dependencies = []

    for job in task_order:
        for essential_dir in slurm_data[job]["essential_dirs"]:
            dependencies = slurmify(
                task_dir=slurm_data[job]["task_dir"],
                task_name=slurm_data[job]["task_name"],
                task_type=job,
                essential_dirs=essential_dir,
                resources=slurm_data[job]["resources"],
                initial_dependencies=dependencies,
            )

    ###################################################################
    ###          SLURM  WORKFLOW BASH SCRIPT CREATOR                 ##
    ###################################################################

    workflow_data = {
        "workflow_dir": args.output_dir,
        "task_order": task_order,
        "tasks": {
            "preprocessor": {
                "task_dir": parsing_data["jobs"]["preprocessor"]["task_dir"],
                "task_name": parsing_data["jobs"]["preprocessor"]["task_name"],
                "essential_dirs": parsing_data["jobs"]["preprocessor"][
                    "essential_dirs"
                ],
            },
            "alignments": {
                "task_name": parsing_data["jobs"]["alignments"]["task_name"],
                "task_dir": parsing_data["jobs"]["alignments"]["task_dir"],
                "essential_dirs": parsing_data["jobs"]["alignments"]["essential_dirs"],
            },
            "merging": {
                "task_name": parsing_data["jobs"]["merging"]["task_name"],
                "task_dir": parsing_data["jobs"]["merging"]["task_dir"],
                "essential_dirs": parsing_data["jobs"]["merging"]["essential_dirs"],
            },
        },
    }
    create_workflow_script(**workflow_data)
