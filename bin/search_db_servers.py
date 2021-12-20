#!/usr/bin/env python3
""" Wrapper of dump_genome_from_core.pl to dump a list of FASTA file
"""
import argparse
import subprocess
import os
import sys

try:
    import yaml
    from yaml.loader import SafeLoader
except ModuleNotFoundError as err:
    # Error handling
    print(err)
    print('Please, run "pip install PyYAML" to install PyYAML module')



def subprocess_call(command, work_dir=None, shell=False, ibsub=False):
    """Subprocess function to spin  the given command line`

    Args:
        command: the command that the subprocess will spin
        work_dir: the location where the command should be run
        shell: if shell is True, the specified command will be executed through the shell.
        ibsub: if ibsub is True, the command will be called via ibsub

    Returns:
        The subprocess output or None otherwise

    """

    if ibsub:
        command = ["ibsub", "-d"] + command

    call = command
    print("Running: {}".format(" ".join(call)))

    with subprocess.Popen(
        call,
        shell=shell,
        encoding="ascii",
        cwd=work_dir,
        stdout=subprocess.PIPE,
        universal_newlines=True,
    ) as process:

        output, stderr = process.communicate()

        process.wait()
        if process.returncode != 0:
            out = "stdout={}".format(output)
            out += ", stderr={}".format(stderr)
            raise RuntimeError(
                "Command {} exited {}: {}".format(call, process.returncode, out)
            )

        print("Successfully ran: {}".format(" ".join(call)))

        return output.strip()
    return None




def find_server(specie, server_group, regex):
    dbc_search_call = [
        "dbc_search",
        "-g {0}".format(server_group),
        "{0}{1}".format(specie, regex)
    ]
    return subprocess_call(dbc_search_call, shell=True)


def parse(species, server_group, regex=''):
    
    data = {}

    for specie in species:
        result = find_server(specie, server_group, regex)
        
        if result:
            server, db_name = list(filter(None,result.splitlines()))[0].split()
            if server not in data:
                data[server] = []
            data[server].append(db_name)
    
    print(data)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--file", required=True, type=str, help="List of species")
    parser.add_argument("--group", required=False, type=str, help="Server group to search")
    parser.add_argument("--regex", required=False, type=str, help="Regex filter to add in the search")
    parser.add_argument(
        "--output", required=False, default=None, type=str, help="Output folder to save the results in YAML format"
    )
    args = parser.parse_args()

    with open(args.file, mode="r", encoding="utf-8") as f:
        species = f.read().split()

        
        args.output = os.path.dirname(os.path.realpath(f.name)) if args.output is None else os.path.abspath(args.output)
    
        if not os.path.isdir(args.output):
            print(
                "{} folder does not exist for output, please create it first".format(
                    args.output
                )
            )
            sys.exit(1)
        

        parse(species, "all", "%%core")