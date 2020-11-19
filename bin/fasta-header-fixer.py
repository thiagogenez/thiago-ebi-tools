import fileinput
import argparse
import os.path
import sys
import uuid

if __name__ == "__main__":

    parser = argparse.ArgumentParser()
    parser.add_argument("input", help = "FAST file")
    args = parser.parse_args()

    if not os.path.exists(args.input):
        print('File {} does not exist!'.format(args.input))
        sys.exit(1)

    output = str(uuid.uuid4())
    f = open(output, "w")

    for line in fileinput.input(args.input):
        if line[0] == '>':
            line = line.split()[0] + '\n'
        f.write(line)

    f.close()

    #rename files
    tmp_filename = str(uuid.uuid4())

    os.rename(args.input,tmp_filename)
    os.rename(output, args.input)
    os.remove(tmp_filename)