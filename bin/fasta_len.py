#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
from Bio.SeqIO.FastaIO import SimpleFastaParser
import si_prefix

FastaFile = open(sys.argv[1], 'r')


total = 0

for name, seq in SimpleFastaParser(FastaFile):
    seqLen = len(seq)
    total = total + seqLen
    print('name: {}\tlen: {}\t -> {}'.format(name,seqLen, si_prefix.si_format(seqLen)))

FastaFile.close()


print('Total: {} -> {}'.format(total, si_prefix.si_format(total)))
