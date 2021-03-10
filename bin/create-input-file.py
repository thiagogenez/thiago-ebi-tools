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
    args.output = args.treeFile + '.processed.txt'
  
  f = open(args.output, "w")  
  
  f.write('# File auto-generated On {}\n'.format(datetime.now().strftime("%d/%m/%Y %H:%M:%S")))
  f.write('# Command: {}\n'.format(' '.join(sys.argv)))
  f.write('#\n') 

  with open(args.treeFile) as file:
    nodes = file.readlines()
    f.write(nodes[0])

    body = nodes[0].strip().replace('(','').replace(')','').replace(';','').split(',')
    body = [i.split(':')[0] for i in body]

  d = dict()

  for file in fasta_files:
    key = file.lower().split('.')[0]
    d[key] = '{}/{}'.format(args.fastaPath, file)

  for row in body:
    key = row.lower()
    if key in d:
      f.write('{} {}\n'.format(row, d[key]))

  f.close()
