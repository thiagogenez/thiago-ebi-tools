#!/usr/bin/env python3

import fileinput
import argparse
import os
import sys
import uuid
import re
from datetime import datetime

# check if biopython package is installed
try:
    from Bio import Phylo
except ImportError as e:
    raise e



def create_fasta_contents(dest, ext):
    dest = os.path.abspath(dest)

    try:
        filenames = os.listdir(dest)
    except FileNotFoundError as err:
        raise err

    content = dict()
    
    for filename in filenames:
        if filename.endswith(ext):
            
            key = re.sub('\W+|_','', filename ).lower()
            
            content[key] = {
                'path' : '{}/{}'.format(dest, filename),
                'name' : filename.rsplit(ext, 1)[0]
            }
    
    return content



def get_tree_contents(filename, format, output):
    
    with open(filename, mode='r') as f:
        
        if output is None:
            output = os.path.dirname(os.path.realpath(f.name))
        else:
            output = os.path.abspath(output)
    
        name, ext = os.path.splitext(os.path.basename(f.name))
        output += '/{}.processed{}'.format(name, ext)
        tree = Phylo.read(f, format=format)

    return {
        'tree': tree,
        'path': output
    }

def create_new_tree(tree_content, fasta_content, format):
    
    for leaf in tree_content['tree'].get_terminals():
        
        name = re.sub('\W+|_','', leaf.name ).lower()
        found = False
        for key, fasta in fasta_content.items():
            if name in key:
                leaf.name = fasta['name']
                found = True
                break

        if not found:
            print('Not match any for {}'.format(leaf.name))
        
    Phylo.write(trees=tree_content['tree'], file=tree_content['path'], format=format, format_branch_length='%s',format_confidence="%s")


def append_fasta_paths(filename, fasta_content):
    
    with open(filename, mode='a') as f:
        for fasta in fasta_content.values():
            f.write('{} {}\n'.format(fasta['name'], fasta['path']))

def add_makeup(new_filename, old_filename, argv):

    with open(new_filename, mode='r') as f:
        new_content = f.read()
    
    with open(old_filename, mode='r') as f:
        old_content = f.read()

    with open(new_filename, mode='w+') as f:
        f.write('# File generated On {}\n'.format(datetime.now().strftime("%d/%m/%Y %H:%M:%S")))
        f.write('# by the following command: {}\n'.format(' '.join(argv)))
        f.write('#\n')
        f.write('# Original tree:')
        f.write('\n# {}'.format(old_content))
        f.write('#\n')
        f.write(new_content)

if __name__ == "__main__":

    parser = argparse.ArgumentParser()
    parser.add_argument('--fastas', type=str, required=True, help='Directory where FAST files are localised')
    parser.add_argument('--extension', type=str, required=False, default='.fa', help='FAST filename extension')
    parser.add_argument('--tree', type=str, required=True, help='File that describes the tree')
    parser.add_argument('--format', type=str, required=False, default='newick', help='Format of the tree')
    parser.add_argument('--output', type=str, default=None, help='Processed output file')

    args = parser.parse_args()

    fasta_content  = create_fasta_contents(dest=args.fastas, ext=args.extension)
    tree_content = get_tree_contents(filename=args.tree, format=args.format, output=args.output)
    create_new_tree(tree_content, fasta_content, args.format)
    append_fasta_paths(tree_content['path'], fasta_content)
    add_makeup(tree_content['path'], args.tree, sys.argv)

    #print(fasta_filenames)
    #print(tree)

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
