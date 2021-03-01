
import numpy as np
import argparse
import re
# import bz2
import sys
import os
import csv


this_directory = os.path.dirname(os.path.realpath(__file__)) + "/"
this_filename = sys.argv[0].split('/')[-1]

project_dir = this_directory + '../../'

parser = argparse.ArgumentParser(description='Parse the raw files and generate CSV files.',
                                 usage='python {} -i results/'.format(this_filename))

parser.add_argument('-i', '--indir', type=str, default=os.path.join(project_dir, 'results/run'),
                    help='The directory with the results.')

parser.add_argument('-o', '--outdir', type=str, default=os.path.join(project_dir, 'results/csv'),
                    help='The directory to store the csv files.')


regexps = {
    r'.*Recv\sPacket\s(\d+),\sAverage\slen\s(.*),\sIO\sSpeed\s(.*)Gbps.*': ['RcvPkt', 'RcvLen', 'RcvIO'],
    r'.*Send\sPacket\s(\d+),\sAverage\slen\s(.*),\sIO\sSpeed\s(.*)Gbps.*': ['SndPkt', 'SndLen', 'SndIO'],
    r'.*elapsed time : (.*) us, average cycle time (.*)\s*': ['Time', 'AvgCycle'],
    r'\s*(\d+) search jobs, speed is (.*) Mops.*': ['SrcJ', 'SrcSpd'],
    r'\s*(\d+) insert jobs, speed is (.*) Mops.*': ['InsJ', 'InsSpd'],
    r'\s*total search and insert speed is (.*) Mops.*': ['SrcInsSpd'],
    r'\s*Average batch search (.*), insert (.*), delete (.*)\..*': ['BtchSrc', 'BtchIns', 'BtchDel'],
    # r'insert time, num (\d+), total (.*) us, average (.*) us, num elem (.*),.*': [''],
    # r'delete time, total (.*) us, average (.*) us, num elem (.*),.*': [],
    # r'search time, total (.*) us, average (.*) us.*': [],
}

# header = ['Time', 'SrcJ', 'InsJ', 'SrcSpd', 'InsSpd', 'SrcInsSpd', 'SrcBW', 'InsBW', 'SrcInsBW', 'SrcLat',
# titlereg = 'USE_LOCK(.*)-TWO_PORTS(.*)-SIGNATURE(.*)-PRELOAD(.*)-PREFETCH_PIPELINE(.*)-PREFETCH_BATCH(.*)-NOT_FORWARD(.*)-NOT_COLLECT(.*)-NOT_GPU(.*)-COMPACT_JOB(.*)-KEY_MATCH(.*)-KVSIZE(.*)-GET(.*)-GPUSTHR(.*)-GPUDTHR(.*)-GPUTHRPERBLK(.*)-NUM_QUEUE_PER_PORT(.*)-MAX_WORKER_NUM(.*)'
titlereg = r'.*PRELOAD(.*)-PREFETCH_PIPELINE.*-KVSIZE(\d+).*GET(\d+).*'

formatter = {
    'RcvPkt': '{:.0f}',
    'RcvLen': '{:.2f}',
    'RcvIO': '{:.3f}',
    'SndPkt': '{:.0f}',
    'SndLen': '{:.2f}',
    'SndIO': '{:.3f}',
    'Time': '{:.0f}',
    'AvgCycle': '{:.2f}',
    'SrcJ': '{:.0f}',
    'SrcSpd': '{:.3f}',
    'InsJ': '{:.0f}',
    'InsSpd': '{:.3f}',
    'SrcInsSpd': '{:.3f}',
    'BtchSrc': '{:.2f}',
    'BtchIns': '{:.2f}',
    'BtchDel': '{:.2f}'
}

kvsize = {
    0: (8, 8),
    1: (16, 64),
    2: (32, 512),
    3: (128, 1024),
    4: (32, 100),
    5: (33, 100),
    6: (1, 4),
    7: (1, 1),
    8: (1, 32),
    9: (32, 512),
    10: (32, 1024)
}


def set_len(kvarg):
    return kvsize[int(kvarg)][0] + kvsize[int(kvarg)][1] + 8


def get_len(kvarg):
    return kvsize[int(kvarg)][0] + 4


if __name__ == '__main__':
    args = parser.parse_args()
    indir = args.indir
    outdir = args.outdir
    if not os.path.exists(outdir):
        os.makedirs(outdir)

    # compile all the regexps
    header = []
    tempdir = {}
    for k, v in regexps.items():
        tempdir[re.compile(k)] = v
        header += v
    regexps = tempdir
    titlereg = re.compile(titlereg)

    # start scanning the files
    for infile in os.listdir(indir):
        # print(infile)
        if '.txt' not in infile:
            continue
        # kvarg = infile.split('KVSIZE')[1].split('-')[0]
        match = titlereg.search(infile)
        preload, kvarg, get = match.groups()
        key_len, val_len = kvsize[int(kvarg)]
        get = int(get)
        set = 100 - get
        
        preload = preload == ''

        # print(f'k-v: {key_len}-{val_len}')

        lines = open(os.path.join(indir, infile), 'r').readlines()
        records = []
        csv_line = [0]*len(header)
        num_values = 0
        first_batch = True
        for line in lines:
            if preload:
                if 'Hash table has been loaded' not in line:
                    continue
                else:
                    preload = False
            # check against all regexps
            for k, v in regexps.items():
                res = k.search(line)
                # if we match
                if res != None:
                    assert(len(res.groups()) == len(v))
                    # we copy the matched values to the right places
                    for m, h in zip(res.groups(), v):
                        if h == 'Time':
                            m = float(m)/1e6  # transform to sec
                        csv_line[header.index(h)] = formatter[h].format(
                            float(m))
                    num_values += len(v)
                if num_values == len(header):
                    if first_batch:
                        first_batch = False
                    else:
                        # here add the SrcBW, InsBW, SrcInsBW
                        srcspd = float(
                            csv_line[header.index('SrcSpd')])  # in Mops
                        insspd = float(
                            csv_line[header.index('InsSpd')])  # in Mops
                        # this is in mil bytes/s
                        srcbw = f'{srcspd * get_len(kvarg) / 8:.3f}'
                        # this is in mil bytes/s
                        insbw = f'{insspd * set_len(kvarg) / 8:.3f}'
                        srcinsbw = f'{float(srcbw) + float(insbw):.3f}'
                        try:
                            srclat = f'{1e3 / srcspd:.3f}'  # in nanoseconds
                        except ZeroDivisionError as e:
                            srclat = float('NaN')
                        try:
                            inslat = f'{1e3 / insspd:.3f}'  # in nanoseconds
                        except ZeroDivisionError as e:
                            inslat = float('NaN')

                        csv_line += [str(srcbw), str(insbw),
                                     str(srcinsbw), str(srclat), str(inslat)]
                        records.append(csv_line)
                    csv_line = [0]*len(header)
                    num_values = 0

            # write the extacted data in the csv file
            # outfile = infile.replace('.txt', '.csv')
            # outfile = infile.split('KEY_MATCH-')[1].split('-GPUSTHR')[0]
            outfile = f'k{key_len}-v{val_len}-g{get}-s{set}.csv'
            outfile = os.path.join(outdir, outfile)
            outfile = open(outfile, 'w')
            writer = csv.writer(outfile, delimiter='\t')
            writer.writerow(['N', 'B', 'Gbps', 'N', 'B', 'Gbps',
                             's', 'us', 'N', 'Mops', 'N', 'Mops',
                             'Mops', 'N', 'N', 'N', 'MB/s', 'MB/s', 'MB/s',
                             'us', 'us'])
            writer.writerow(
                header+['SrcBW', 'InsBW', 'SrcInsBW', 'SrcLat', 'InsLat'])
            writer.writerows(records)
            outfile.close()

# def extract_single_file_no_activity(infile):
#     re_kernel = 'GPGPU-Sim uArch:\s*Shader\s*(\d+).*kernel\s*(\d+)\s*\'(.*)\'.*'
#     re_kernel = re.compile(re_kernel)

#     re_init = 'GPGPU-Sim Cycle ([0-9]+).*LIVENESS.*Core\s*(\d+).*cta:\s*(\d+).*start_tid:\s*(\d+).*end_tid:\s*(\d+).*'
#     re_init = re.compile(re_init)

#     re_finish = 'GPGPU-Sim Cycle ([0-9]+).*LIVENESS.*Core\s*(\d+).*Finished.*CTA\s*#(\d+).*'
#     re_finish = re.compile(re_finish)

#     data = {}

#     if 'bz2' in infile:
#         file = bz2.BZ2File(infile, 'r')
#     else:
#         file = open(infile, 'r')

#     active_kernel = None

#     for line in file:
#         if 'GPGPU-Sim' not in line:
#             continue

#         if (re_kernel.search(line)):
#             match = re_kernel.search(line)
#             # We have an kernel line
#             shader, kernel_id, kernel_name = match.groups()
#             active_kernel = kernel_name
#             if kernel_name not in data:
#                 data[kernel_name] = {
#                     'ids': [],
#                     'shaders': [],
#                     'cycles': [],
#                     'threads': [],
#                     'ctas': {}
#                 }

#             data[kernel_name]['shaders'].append(shader)
#             data[kernel_name]['ids'].append(kernel_id)

#         elif (re_init.search(line)):
#             match = re_init.search(line)
#             # We have an issue line
#             cycle, core, cta, start_tid, end_tid = match.groups()
#             start_tid = int(start_tid)
#             end_tid = int(end_tid)
#             assert(active_kernel in data)
#             threads = end_tid - start_tid
#             data[active_kernel]['ctas'][cta] = threads
#             if len(data[active_kernel]['cycles']) > 0:
#                 assert(int(cycle) > int(data[active_kernel]['cycles'][-1]))
#             data[active_kernel]['cycles'].append(cycle)
#             data[active_kernel]['threads'].append(threads)

#         elif (re_finish.search(line)):
#             match = re_finish.search(line)
#             cycle, core, cta = match.groups()
#             assert(active_kernel in data)
#             assert(len(data[active_kernel]['cycles']) > 0)
#             data[active_kernel]['cycles'].append(cycle)
#             data[active_kernel]['threads'].append(
#                 -data[active_kernel]['ctas'][cta])

#     file.close()
#     records = []
#     header = ['kernel_name', 'kernel_ids',
#               'cycles', 'active_threads', 'shader_cores']
#     for kname, kernel_data in data.items():
#         threads = np.cumsum(kernel_data['threads'])
#         ids = '|'.join(kernel_data['ids'])
#         threads = '|'.join(threads.astype(str))
#         cycles = '|'.join(kernel_data['cycles'])
#         shaders = '|'.join(kernel_data['shaders'])
#         records.append([kname, ids, cycles, threads, shaders])

#     return header, records


# def extract_single_file_with_activity(infile):
#     re_kernel = 'GPGPU-Sim uArch:\s*Shader\s*(\d+).*kernel\s*(\d+)\s*\'(.*)\'.*'
#     re_kernel = re.compile(re_kernel)

#     re_init = 'GPGPU-Sim Cycle ([0-9]+).*LIVENESS.*Core\s(\d+).*Active_warps\s(\d+)'
#     re_init = re.compile(re_init)

#     data = {}

#     if 'bz2' in infile:
#         file = bz2.BZ2File(infile, 'r')
#     else:
#         file = open(infile, 'r')

#     active_kernel = None
#     active_shader = 0

#     for line in file:
#         if 'GPGPU-Sim' not in line:
#             continue

#         if (re_kernel.search(line)):
#             match = re_kernel.search(line)
#             # We have an kernel line
#             shader, kernel_id, kernel_name = match.groups()
#             if int(shader) != active_shader:
#                 continue
#             active_kernel = kernel_name
#             if kernel_name not in data:
#                 data[kernel_name] = {
#                     'ids': [],
#                     'cycles': [],
#                     'warps': [],
#                 }

#             # data[kernel_name]['shaders'].append(shader)
#             data[kernel_name]['ids'].append(kernel_id)

#         elif (re_init.search(line)):
#             match = re_init.search(line)
#             # We have an issue line
#             cycle, shader, warps = match.groups()
#             # shader = 0
#             if (int(shader) != active_shader) or (active_kernel not in data):
#                 continue
#             if len(data[active_kernel]['cycles']) > 0:
#                 if warps == data[active_kernel]['warps'][-1]:
#                     continue
#             data[active_kernel]['cycles'].append(cycle)
#             data[active_kernel]['warps'].append(warps)

#     file.close()
#     records = []
#     header = ['kernel_name', 'kernel_ids', 'cycles', 'warps']
#     for kname, kernel_data in data.items():
#         ids = '|'.join(kernel_data['ids'])
#         warps = '|'.join(kernel_data['warps'])
#         cycles = '|'.join(kernel_data['cycles'])
#         records.append([kname, ids, cycles, warps])

#     return header, records


# extract_single_file = extract_single_file_with_activity


# if __name__ == '__main__':
#     parser = argparse.ArgumentParser(
#         description='Analyze the output file to re-construct an active warps trace.')

#     parser.add_argument('-i', '--infile', type=str, default=None,
#                         help='Input file.')

#     parser.add_argument('-o', '--outfile', type=str, default='stdout',
#                         help='The output result file.')

#     parser.add_argument('-noactivity', '--no-activity-report',
#                         action='store_true',
#                         help='The simulation was not run with warp activity report.')

#     args = parser.parse_args()

#     infile = args.infile
#     outfile = args.outfile

#     if args.no_activity_report:
#         extract_single_file = extract_single_file_no_activity
#     header, records = extract_single_file(infile)

#     print_str = '\t'.join(header) + '\n'
#     for r in records:
#         print_str += '\t'.join(r) + '\n'

#     if outfile == 'stdout':
#         print(print_str)
#     else:
#         import csv
#         file = open(outfile, 'w')
#         writer = csv.writer(file, delimiter='\t')
#         writer.writerow(header)
#         writer.writerows(records)
#         file.close()
