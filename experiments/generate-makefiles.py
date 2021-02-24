import numpy as np
import re
import os
import sys
import argparse
import itertools

this_directory = os.path.dirname(os.path.realpath(__file__)) + "/"
this_filename = sys.argv[0].split('/')[-1]

project_dir = this_directory + '../../'

parser = argparse.ArgumentParser(description='Generate makefiles according to input configuration.',
                                 usage='python {} -i results/'.format(this_filename))

parser.add_argument('-i', '--inputfile', type=str, default=os.path.join(project_dir, 'Makefile-template'),
                    help='The template Makefile.')

parser.add_argument('-o', '--outdir', type=str, default=project_dir,
                    help='The output directory.')

args = parser.parse_args()

if not os.path.exists(args.outdir):
    os.makedirs(args.outdir)

# key (search term) -> list of values (to replace)

kvconfigs = {
    "-DUSE_LOCK": [''],
    "-DTWO_PORTS": ['_0'],
    "-DSIGNATURE": ['_0'],
    "-DPRELOAD": ['_0'],
    "-DPREFETCH_PIPELINE": ['_0'],
    "-DPREFETCH_BATCH": [''],
    "-DNOT_FORWARD": ['_0'], 
    "-DNOT_COLLECT": ['_0'],
    "-DNOT_GPU": ['_0'],
    "-DCOMPACT_JOB": ['_0'],
    "-DKEY_MATCH": [''],
    # "-DKVSIZE": ['4', '5', '6', '7', '8', '9', '10'],
    "-DKVSIZE": ['4', '6', '8', '9', '10'],
    # "-DGET": ['50', '90', '95'],
    "-DGET": ['50', '90', '95'],
    # "-DGPUSTHR": ['61440', '24576'],
    "-DGPUSTHR": ['61440'],
    "-DGPUDTHR": ['16384'],
    # "-DGPUTHRPERBLK": ['256', '512', '1024'],
    "-DGPUTHRPERBLK": ['1024'],
    "-DNUM_QUEUE_PER_PORT":['9'],
    "-DMAX_WORKER_NUM":['16']
}

if __name__ == '__main__':
    keylist = list(kvconfigs.keys())
    valuelist = list(kvconfigs.values())

    regex = '|'.join(keylist)
    regex = re.compile(regex)


    # Read the input Makefile
    with open(args.inputfile) as f:
        basemkfile = f.readlines()
    # generate all the configurations
    all_configs = list(itertools.product(*valuelist))
    print(all_configs)
    # print(len(all_configs))
    for i, config in enumerate(all_configs):
        str = ''
        for k, v in zip(keylist, config):
            str += f'{k}:{v},\t'
        str = str[:-2]
        print(f'[{i}]\t'+str)
        name = 'Makefile_'+str
        name = name.replace('\t','').replace(':','').replace('-D','').replace(',','-')
        # generate all the makefiles
        # newmkfile = basemkfile.copy()
        newmkfile = []
        for line in basemkfile:
            res = regex.search(line)
            if res != None:
                key = res.group()
                value = config[keylist.index(key)]
                line = line.replace('{XXX}', value)
            newmkfile.append(line)
            # if regex.match(line)
        # print(newmkfile)
        with open(os.path.join(args.outdir, name), 'w') as f:
            f.writelines(newmkfile)

