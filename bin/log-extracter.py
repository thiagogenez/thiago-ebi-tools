#!/usr/bin/env python3

import fileinput
import argparse
import os.path
import sys

from collections import OrderedDict
from statistics import mean, pstdev


if __name__ == "__main__":

    parser = argparse.ArgumentParser()
    parser.add_argument("input", help = "log file")
    args = parser.parse_args()

    if not os.path.exists(args.input):
        print('File {} does not exist!'.format(args.input))
        sys.exit(1)

    table = OrderedDict()

    for line in fileinput.input(args.input):
        if 'Successfully ran:' in line:
            line = (line.strip())

            line = line.split('ran:')[1].split()
            job = line[0]

            assert line[-1] == 'seconds'
            time = float(line[-2])

            if job in table:
                table[job].append(time)
            else:
                table[job] = [time]



    for item in table.keys():
        print('Job {} executed {} times with a duration of {:.2f} seconds [+- {:.2f} seconds]'.format(item,len(table[item]),mean(table[item]), pstdev(table[item])))
