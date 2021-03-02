import os
import argparse
import subprocess
# import numpy as np
# import re
# import sys
# import itertools

this_directory = os.getcwd()
# this_filename = sys.argv[0].split('/')[-1]

project_dir = this_directory + '../../'

parser = argparse.ArgumentParser(description='Generate makefiles according to input configuration.',
                                 usage='python script.py -i results/')

parser.add_argument('-m', '--makefiles', type=str, default=os.path.join(project_dir, 'experiments/makefiles'),
                    help='All makefiles.')

parser.add_argument('-s', '--run-succesfully', type=str, default='results/run',
                    help='Succesful runs.')

parser.add_argument('-o', '--outdir', type=str, default=os.path.join(project_dir, 'experiments/remaining-makefiles'),
                    help='Store the remaining makefiles.')



if __name__ == '__main__':
    args = parser.parse_args()

    if not os.path.exists(args.outdir):
        os.makedirs(args.outdir)
    
    all_mkfiles = os.listdir(args.makefiles)
    run_mkfiles = os.listdir(args.run_succesfully)
    run_mkfiles = [f'Makefile_{m.replace(".txt","")}' for m in run_mkfiles]

    remaining_mkfiles = set(all_mkfiles) - set(run_mkfiles)

    for mkfile in remaining_mkfiles:
        mkfile = os.path.join(args.makefiles, mkfile)
        cmd = f'cp {mkfile} {args.outdir}/'
        subprocess.run(cmd, shell=True)


