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

            key = re.sub('\\W+|_', '', filename).lower()

            content[key] = {
                'path': '{}/{}'.format(dest, filename),
                'name': filename.rsplit(ext, 1)[0],
                'used': False
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

        name = re.sub('\\W+|_', '', leaf.name).lower()
        for key, fasta in fasta_content.items():
            if name in key:
                leaf.name = fasta['name']
                fasta['used'] = True
                break

        if not fasta['used']:
            print('Not match any for {}'.format(leaf.name))

    Phylo.write(
        trees=tree_content['tree'],
        file=tree_content['path'],
        format=format,
        format_branch_length='%s',
        format_confidence="%s")

    # sanity check
    filenames_not_used = []
    for fasta in fasta_content.values():
        if not fasta['used']:
            print('FASTA file not used in the tree: {}'.format(fasta['name']))
            filenames_not_used.append(fasta)

    return filenames_not_used


def append_fasta_paths(filename, fasta_content):

    with open(filename, mode='a') as f:
        for fasta in fasta_content.values():
            f.write('{} {}\n'.format(fasta['name'], fasta['path']))


def add_makeup(
        new_filename,
        old_filename,
        argv,
        qtd_files,
        qtd_terminals,
        files_not_used):

    with open(new_filename, mode='r') as f:
        new_content = f.read()

    with open(old_filename, mode='r') as f:
        old_content = f.read()

    with open(new_filename, mode='w+') as f:
        f.write('# File generated On {}\n'.format(
            datetime.now().strftime("%d/%m/%Y %H:%M:%S")))
        f.write('# by the following command: {}\n'.format(' '.join(argv)))
        f.write('#\n')
        f.write('# Original tree:')
        f.write('\n# {}'.format(old_content))
        f.write('#\n')
        f.write(
            '# Tree below contains files={} and terminals={}'.format(
                qtd_files, qtd_terminals))
        f.write('\n# Files not used: \n')
        for fasta in files_not_used:
            f.write('# {} {}\n'.format(fasta['name'], fasta['path']))
        f.write('#\n')
        f.write(new_content)


if __name__ == "__main__":

    parser = argparse.ArgumentParser()
    parser.add_argument(
        '--fastas',
        type=str,
        required=True,
        help='Directory where FAST files are localised')
    parser.add_argument(
        '--extension',
        type=str,
        required=False,
        default='.fa',
        help='FAST filename extension')
    parser.add_argument('--tree', type=str, required=True,
                        help='File that describes the tree')
    parser.add_argument(
        '--format',
        type=str,
        required=False,
        default='newick',
        help='Format of the tree')
    parser.add_argument(
        '--output',
        type=str,
        default=None,
        help='Processed output file')

    args = parser.parse_args()

    fasta_content = create_fasta_contents(dest=args.fastas, ext=args.extension)
    tree_content = get_tree_contents(
        filename=args.tree,
        format=args.format,
        output=args.output)
    files_not_used = create_new_tree(tree_content, fasta_content, args.format)
    append_fasta_paths(tree_content['path'], fasta_content)
    add_makeup(new_filename=tree_content['path'],
               old_filename=args.tree,
               argv=sys.argv,
               qtd_files=len(fasta_content),
               qtd_terminals=len(tree_content['tree'].get_terminals()),
               files_not_used=files_not_used)
