#!/usr/bin/env python3

import fileinput
import argparse
import os
import sys
import uuid
import re
from datetime import datetime

try:
    from Bio import Phylo
except ImportError as e:
    raise e

def is_fasta_file(filename):
    return filename.endswith('.fa')

def get_fasta_filenames(dest):

    dest = os.path.abspath(dest)

    try:
        filenames = os.listdir(dest)
    except FileNotFoundError as err:
        raise err

    d = {}
    for filename in filenames:
        if is_fasta_file(filename):
            key = re.sub('\W+','', filename )
            d[key] = '{}/{}'.format(dest, filename)

    return d

def get_newick_tree(file):
   return file.readlines()[0].strip()


if __name__ == "__main__":

    parser = argparse.ArgumentParser()
    parser.add_argument('--fastas', type=str, required=True, help='Directory where FAST files are localised')
    parser.add_argument('--tree', type=str, required=True, help='File that describes the NEWICK tree')
    parser.add_argument('--output', type=str, default=None, help='Processed output file')

    args = parser.parse_args()

    with open(args.tree, mode='r') as f:
        
        if args.output is None:
            args.output = os.path.dirname(os.path.realpath(f.name))
        else:
            args.output = os.path.abspath(args.output)
    
        filenames  = get_fasta_filenames(dest=args.fastas)
        tree = get_newick_tree(f)
    print(filenames)
    print(tree)

  #try:
  #  fasta_files = os.listdir(args.fastaPath)
  #except FileNotFoundError as not_found:
  #  print(args.fastaPath)


  #not_fasta = []
  #for file in fasta_files:
  #  if not file.endswith('.fa'):
  #      not_fasta.append(file)
  #      print('{} is not a fasta file'.format(file))
  

  #for file in not_fasta:
  #  fasta_files.remove(file)

  #if args.output is None:
  #  if '.' in args.treeFile:
  #      filename = args.treeFile.split('.')[0]
  #  args.output = filename + '.processed.txt'
  
  #f = open(args.output, "w")  
  
  #f.write('# File generated On {}\n'.format(datetime.now().strftime("%d/%m/%Y %H:%M:%S")))
  #f.write('# by the following command: {}\n'.format(' '.join(sys.argv)))
  #f.write('#\n') 

  #with open(args.treeFile) as file:
    #nodes = file.readlines()
    #f.write(nodes[0])

   # body = nodes[0].strip().replace('(','').replace(')','').replace(';','').split(',')
   # body = [i.split(':')[0].strip() for i in body]
  #d = dict()

  #for file in fasta_files:
  #  names = file.lower().split('.')
  #  d[(names[0],names[1])] = '{}/{}'.format(args.fastaPath, file)

  #for row in body:
  #  fasta = row.lower()
  #  for key, value in d.items():
  #      if fasta in key[0]:
  #          f.write('{} {}\n'.format(row, value))

  #f.close()
