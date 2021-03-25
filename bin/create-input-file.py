#!/usr/bin/env python3

import fileinput
import argparse
import os.path
import sys
import uuid
from datetime import datetime

if __name__ == "__main__":

  parser = argparse.ArgumentParser()
  parser.add_argument('--fastaPath', type=str, nargs='?', help='Directory where FAST files are localised')
  parser.add_argument('--treeFile', type=str, nargs='?', help='File that describes the NEWICK tree')
  parser.add_argument('--output', type=str, nargs='?', help='Processed output file')
  args = parser.parse_args()

  if not os.path.exists(args.treeFile):
    print('File {} does not exist!'.format(args.treeFile))
    sys.exit(1)

  try:
    fasta_files = os.listdir(args.fastaPath)
  except FileNotFoundError as not_found:
    print(args.fastaPath)

  if args.output is None:
    if '.' in args.treeFile:
        filename = args.treeFile.split('.')[0]
    args.output = filename + '.processed.txt'
  
  f = open(args.output, "w")  
  
  f.write('# File generated On {}\n'.format(datetime.now().strftime("%d/%m/%Y %H:%M:%S")))
  f.write('# by the following command: {}\n'.format(' '.join(sys.argv)))
  f.write('#\n') 

  with open(args.treeFile) as file:
    nodes = file.readlines()
    f.write(nodes[0])

    body = nodes[0].strip().replace('(','').replace(')','').replace(';','').split(',')
    body = [i.split(':')[0].strip() for i in body]

  d = dict()

  for file in fasta_files:
    names = file.lower().split('.')
    d[(names[0],names[1])] = '{}/{}'.format(args.fastaPath, file)

  for row in body:
    fasta = row.lower()
    for key, value in d.items():
        if fasta in key:
            f.write('{} {}\n'.format(row, value))

  f.close()
