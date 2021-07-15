#!/usr/bin/env python3

import fileinput
import argparse
import subprocess
import os.path

import yaml
from yaml.loader import SafeLoader

PERL_SCRIPT = "/hps/software/users/ensembl/repositories/compara/thiagogenez/master/ensembl-compara/scripts/dumps/dump_genome_from_core.pl"


def subprocess_call(parameters,shell=False):
    call = parameters
    process = subprocess.Popen(
        call,
        shell=shell,
        encoding="ascii",
        #stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        universal_newlines=True
        #stderr=errfile
    )

    ## Talk with the process command 
    #try:
    output, stderr = process.communicate()
    #except subprocess.TimeoutExpired:
    #    process.kill()
    #    output, err = process.communicate()
        
    
    if process.returncode != 0:
        out = "stdout={}".format(output)
        out += ", stderr={}".format(stderr)
        raise RuntimeError("Command {} exited {}: {}".format(call, process.returncode, out))
    else:
        print("Successfully ran: {}".format(' '.join(call)))
    
    return output.strip()


def download_file(host, port, core_db, fasta_filename, mask="soft"):
    perl_call = [
        "perl",
        "{}".format(PERL_SCRIPT),
        "--core_db",
        "{}".format(core_db),
        "--host",
        "{}".format(host),
        "--port",
        "{}".format(port),
        "--mask",
        "{}".format(mask),
        "--outfile",
        "{}".format(fasta_filename)
    ]
    #print(perl_call)
    return subprocess_call(parameters=perl_call, shell=True)

def get_name(host, core_db):
    mysql_call = [
        "{}".format(host),
        "{}".format(core_db),
        "-ss",
        "-e",
        'SELECT meta_value FROM meta WHERE meta_key="species.production_name";',
    ]
    return subprocess_call(parameters=mysql_call)


def parse_yaml(filename):
    with open(filename) as f:
        content = yaml.load(f, Loader=SafeLoader)
        for data in content:

            host = data['host']
            port = data['port']

            for core_db in data['core_db']:
                name = get_name(host=host, core_db=core_db)
                name = name.replace('_','.')
                download_file(
                    host=host,
                    port=port,
                    core_db=core_db,
                    fasta_filename='{}.fa'.format(name)
                )
                print(name)
                return 

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--yaml", type=str, help="YAML input file")
    parser.add_argument("--output", type=str, help="Processed output file")
    args = parser.parse_args()

    parse_yaml(filename=args.yaml)
