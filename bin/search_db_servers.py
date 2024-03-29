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

PORT_NUMBER = {
    "mysql-ens-vertannot-staging": 4573,
    "mysql-ens-sta-5" : 4684, 
    "mysql-ens-genebuild-prod-4": 4530,
    "mysql-ens-genebuild-prod-6": 4532,
    "mysql-ens-sta-1": 4519,
    "mysql-ens-genebuild-prod-3": 4529,
    "mysql-ens-general-prod-1": 4525,
    "mysql-ens-compara-prod-10": 4648
}

def subprocess_call(command, work_dir=None, shell=False, ibsub=False, stdout=subprocess.PIPE, universal_newlines=True):
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
        cwd=work_dir,
        stdout=stdout,
        universal_newlines=universal_newlines,
    ) as process:

        output, stderr = process.communicate()
        process.wait()
        if process.returncode != 0:
            out = "stdout={}".format(output)
            out += ", stderr={}".format(stderr)
            raise RuntimeError(
                "Command {} exited {}: {}".format(call, process.returncode, out)
            )

    return output.strip()




def find_server(specie, server_group, regex_search):
    dbc_search_call = [
        "dbc_search",
    ]

    if server_group:
        dbc_search_call.append("-g")
        dbc_search_call.append(server_group)
    
    if regex_search:
        dbc_search_call.append("{0}{1}".format(specie, regex_search))
    
    return subprocess_call(dbc_search_call, shell=False)

def prepare_yaml(data):
    list = []
    for server in data.keys():
        input = {}
        input['host'] = server
        input['port'] = PORT_NUMBER[server] if server in PORT_NUMBER else 9999
        input['user'] = 'ensro'
        input['core_db'] = data[server]

        list.append(input)
    
    return list


def parse(species, server_group, regex_search=''):
    
    data = {}
    not_found = []

    for specie in species:
        result = find_server(specie, server_group, regex_search)
        if result:
            result = list(filter(None,result.strip().splitlines()))

            # FIXME: give priority to 'ens-sta' servers
            ens_sta = list(filter(lambda k: 'mysql-ens-sta' in k, result))
            if ens_sta:
                result = ens_sta
                

            # FIXME: too hacky and harded-code for the second split using _core_
            # 
            # Out[10]: result
            # ['mysql-ens-genebuild-prod-6 kbillis_trachurus_trachurus_gca905171665v1_core_105',
            # 'mysql-ens-genebuild-prod-3 kbillis_trachurus_trachurus_gca905171665v1_core_105',
            # 'mysql-ens-sta-5 trachurus_trachurus_gca905171665v1_core_104_1',
            # 'mysql-ens-genebuild-prod-1 trachurus_trachurus_gca905171665v1_core_103',
            # 'mysql-ens-genebuild-prod-1 trachurus_trachurus_gca905171665v1_core_103_1']

            # In [13]: sorted(result, key = lambda x: x.split()[1].split('_core_')[1])
            # Out[13]:
            # ['mysql-ens-genebuild-prod-1 trachurus_trachurus_gca905171665v1_core_103',
            # 'mysql-ens-genebuild-prod-1 trachurus_trachurus_gca905171665v1_core_103_1',
            # 'mysql-ens-sta-5 trachurus_trachurus_gca905171665v1_core_104_1',
            # 'mysql-ens-genebuild-prod-6 kbillis_trachurus_trachurus_gca905171665v1_core_105',
            # 'mysql-ens-genebuild-prod-3 kbillis_trachurus_trachurus_gca905171665v1_core_105']

            server, db_name = sorted(result, key = lambda x: x.split()[1].split('_core_')[1])[-1].split()
            print("server: {}, db_name: {}\n".format(server, db_name))

            if server not in data:
                data[server] = []
            data[server].append(db_name)
        else:
            not_found.append(specie)
    
    return data, not_found

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--tree", required=True, type=str, help="Tree")
    parser.add_argument("--server_group", default="genebuild", required=False, type=str, help="Server group to search")
    parser.add_argument("--regex_search", default="_core_", required=False, type=str, help="Regex filter to add in the search")
    parser.add_argument(
        "--output", required=False, default=None, type=str, help="Output folder to save the results in YAML format"
    )
    args = parser.parse_args()

    with open(args.tree, mode="r", encoding="utf-8") as f:
        # get list of species from the tree
        # FIXME: this piece of code assumes the tree is correct!
        species = sorted([i.split(':')[0].replace('(','').lower() for i in  f.read().strip().split(',')])

        args.output = os.path.dirname(os.path.realpath(f.name)) if args.output is None else os.path.abspath(args.output)
    
        if not os.path.isdir(args.output):
            print(
                "{} folder does not exist for output, please create it first".format(
                    args.output
                )
            )
            sys.exit(1)
        

        found, not_found = parse(species, args.server_group, args.regex_search)
        
        # store non found species
        with open('{}.not-found.yaml'.format(args.tree), 'w') as yaml_file:
            yaml.dump(not_found, yaml_file)

        # prepare yaml for species found
        list = prepare_yaml(found)

        # dump the list following the script to download the fasta files
        # "dump_genome_from_core.py"
        for key in found.keys():
            found[key].sort()
        with open('{}.found.yaml'.format(args.tree), 'w') as yaml_file:
            yaml.dump(list, yaml_file)

