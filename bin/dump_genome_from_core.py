#!/usr/bin/env python3

import fileinput
import argparse
import subprocess
import os.path

import yaml
from yaml.loader import SafeLoader

SCRIPT = "/hps/software/users/ensembl/repositories/compara/thiagogenez/master/ensembl-compara/scripts/dumps/dump_genome_from_core.pl"


def subprocess_call(parameters):
    call = parameters
    process = subprocess.Popen(
        call,
        shell=shell,
        encoding="ascii",
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=errfile,
        bufsize=-1,
        cwd=work_dir,
    )


def download_file(host, port, core_db, fasta_filename, mask="soft"):
  perl_call = [
      "perl",
      "--core_db",
      "{}".format(core_db),
      "--host",
      "{}".format(host),
      "--port",
      "{}".format(port),
      "--mask",
      "{}".format(mask),
      "--outfile",
      "{}".format(fasta_filename),
  ]

return subprocess_call(parameters=perl_call)


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
    for data in f:
      host = data['host']
      
      for core_db in data['core_db']
        name = get_name(host=host, core_db=core_db)
        print(name)

if __name__ == "__main__":
  parser = argparse.ArgumentParser()
  parser.add_argument("--yaml", type=str, help="YAML input file")
  parser.add_argument("--output", type=str, help="Processed output file")
  args = parser.parse_args()
