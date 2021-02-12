#!/usr/bin/env python3

import fileinput
import argparse
import os.path
import sys
import uuid

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

  with open(args.treeFile) as file:
    nodes = file.readlines()
    f.write(nodes[0])

    body = nodes[0].strip().replace('(','').replace(')','').replace(';','').split(',')
    body = [i.split(':')[0] for i in body]


  for file in fasta_files:
    for row in body:
      if row == file.lower().split('.')[0]:
        f.write('{} {}/{}\n'.format(row, args.fastaPath, file))

  f.close()
