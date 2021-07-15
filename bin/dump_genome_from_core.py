#!/usr/bin/env python3

import fileinput
import argparse
import subprocess
import os

import yaml
from yaml.loader import SafeLoader

PERL_SCRIPT = "/hps/software/users/ensembl/repositories/compara/thiagogenez/master/ensembl-compara/scripts/dumps/dump_genome_from_core.pl"


def subprocess_call(parameters, work_dir=None, shell=False, ibsub=False):
    if ibsub:
        parameters = ['ibsub', '-d'] + parameters
    
    call = parameters
    print("Running: {}".format(' '.join(call)))
    process = subprocess.Popen(
        call,
        shell=shell,
        encoding="ascii",
        cwd=work_dir, 
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
        
    process.wait()
    if process.returncode != 0:
        out = "stdout={}".format(output)
        out += ", stderr={}".format(stderr)
        raise RuntimeError("Command {} exited {}: {}".format(call, process.returncode, out))
    else:
        print("Successfully ran: {}".format(' '.join(call)))
    
    return output.strip()


def download_file(host, port, core_db, fasta_filename, mask="soft"):
    
    work_dir = '/hps/software/users/ensembl/repositories/compara/thiagogenez/master/ensembl-compara/scripts/dumps'
    script = 'dump_genome_from_core.pl'

    perl_call = [
        "perl",
        "{}/{}".format(work_dir,script),
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
    return subprocess_call(parameters=perl_call, ibsub=True, shell=False)

def get_name(host, core_db):
    mysql_call = [
        "{}".format(host),
        "{}".format(core_db),
        "-ss",
        "-e",
        'SELECT meta_value FROM meta WHERE meta_key="species.production_name";',
    ]
    return subprocess_call(parameters=mysql_call)


def parse_yaml(file, dest):
    
    content = yaml.load(file, Loader=SafeLoader)
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
                fasta_filename='{}/{}.fa'.format(dest,name)
            )

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--yaml", required=True, type=str, help="YAML input file")
    parser.add_argument("--output", required=False, default=None, type=str, help="Processed output file")
    args = parser.parse_args()

    with open(args.yaml, mode='r') as f:

        if args.output is None:
            args.output = os.path.dirname(os.path.realpath(f.name))
        else:
            args.output = os.path.abspath(args.output)
        
        parse_yaml(file=f, dest=args.output)
