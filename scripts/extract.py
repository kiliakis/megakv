
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

parser.add_argument('-i', '--indir', type=str, default=None,
                    help='The directory with the results.')

parser.add_argument('-o', '--outdir', type=str, default=None,
                    help='The directory to store the csv files.')

parser.add_argument('-m', '--monitordir', type=str, default=None,
                    help='The directory with the monitor results.')

parser.add_argument('-mo', '--monitoroutdir', type=str, default=None,
                    help='The directory to save the extracted monitor results.')

parser.add_argument('-l', '--limit', type=int, default=100,
                    help='Time limit when collecting monitor data.')

# header = ['Time', 'SrcJ', 'InsJ', 'SrcSpd', 'InsSpd', 'SrcInsSpd', 'SrcBW', 'InsBW', 'SrcInsBW', 'SrcLat',
# titlereg = 'USE_LOCK(.*)-TWO_PORTS(.*)-SIGNATURE(.*)-PRELOAD(.*)-PREFETCH_PIPELINE(.*)-PREFETCH_BATCH(.*)-NOT_FORWARD(.*)-NOT_COLLECT(.*)-NOT_GPU(.*)-COMPACT_JOB(.*)-KEY_MATCH(.*)-KVSIZE(.*)-GET(.*)-GPUSTHR(.*)-GPUDTHR(.*)-GPUTHRPERBLK(.*)-NUM_QUEUE_PER_PORT(.*)-MAX_WORKER_NUM(.*)'
titleregexp = r'.*PRELOAD(.*)-PREFETCH_PIPELINE.*-KVSIZE(\d+).*GET(\d+).*'


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


def extract_timings(indir, outdir):
    regexps = {
        # r'.*Recv\sPacket\s(\d+),\sAverage\slen\s(.*),\sIO\sSpeed\s(.*)Gbps.*': ['RcvPkt', 'RcvLen', 'RcvIO'],
        # r'.*Send\sPacket\s(\d+),\sAverage\slen\s(.*),\sIO\sSpeed\s(.*)Gbps.*': ['SndPkt', 'SndLen', 'SndIO'],
        # r'.*elapsed time : (.*) us, average cycle time (.*)\s*': ['Time', 'AvgCycle'],)
        r'.*elapsed time : (.*) us, average cycle time.*': ['Time'],
        r'\s*(\d+) search jobs, speed is (.*) Mops.*': ['SrcJ', 'SrcSpd'],
        r'\s*(\d+) insert jobs, speed is (.*) Mops.*': ['InsJ', 'InsSpd'],
        r'\s*total search and insert speed is (.*) Mops.*': ['SrcInsSpd'],
        # r'\s*Average batch search (.*), insert (.*), delete (.*)\..*': ['BtchSrc', 'BtchIns', 'BtchDel'],)
        # r'insert time, num (\d+), total (.*) us, average (.*) us, num elem (.*),.*': [''],
        # r'delete time, total (.*) us, average (.*) us, num elem (.*),.*': [],
        # r'search time, total (.*) us, average (.*) us.*': [],
    }

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

    # compile all the regexps
    header = []
    tempdir = {}
    for k, v in regexps.items():
        tempdir[re.compile(k)] = v
        header += v
    regexps = tempdir
    titlereg = re.compile(titleregexp)

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
                        # if h == 'Time':
                        #     m = float(m)/1e6  # transform to sec
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
                        srcbw = f'{srcspd * get_len(kvarg):.3f}'
                        # this is in mil bytes/s
                        insbw = f'{insspd * set_len(kvarg):.3f}'
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
            # writer.writerow(['N', 'B', 'Gbps', 'N', 'B', 'Gbps',
            #                  's', 'us', 'N', 'Mops', 'N', 'Mops',
            #                  'Mops', 'N', 'N', 'N', 'MB/s', 'MB/s', 'MB/s',
            #                  'us', 'us'])
            writer.writerow(['s', 'N', 'Mops', 'N', 'Mops',
                             'Mops', 'MB/s', 'MB/s', 'MB/s',
                             'ns', 'ns'])

            writer.writerow(
                header+['SrcBW', 'InsBW', 'SrcInsBW', 'SrcLat', 'InsLat'])
            writer.writerows(records)
            outfile.close()


def extract_monitors(indir, outdir):
    header = ['time', 'pwr', 'gtemp', 'sm']
    regexp = r'.*(?P<time>\d+:\d+:\d+)\s+0\s+(?P<pwr>\d+)\s+(?P<gtemp>\d+)\s+-\s+(?P<sm>\d+).*'
    regexp = re.compile(regexp)
    titlereg = re.compile(titleregexp)

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
        start_time = None
        # print(f'k-v: {key_len}-{val_len}')
        records = []
        file = open(os.path.join(indir, infile), 'r')
        line = file.readline()
        limit = args.limit
        while line and limit > 0:
            match = regexp.search(line)
            if match:
                limit-=1
                time = match.group('time')
                pwr = match.group('pwr')
                gtemp = match.group('gtemp')
                sm = int(match.group('sm'))
                time = time.split(':')
                time = int(time[0]) * 3600 + int(time[1]) * 60 + int(time[2])
                if sm > 0:
                    if start_time is None:
                        start_time = time
                    time = time - start_time
                    if len(records) > 0:
                        if time > records[-1][0]:
                            records.append([time, pwr, gtemp, sm])
                    else:
                        records.append([time, pwr, gtemp, sm])

            line = file.readline()
        file.close()
        outfile = f'monitor-k{key_len}-v{val_len}-g{get}-s{set}.csv'
        outfile = os.path.join(outdir, outfile)
        outfile = open(outfile, 'w')
        writer = csv.writer(outfile, delimiter='\t')
        writer.writerow(['sec', 'W', 'C', '%'])
        writer.writerow(header)
        writer.writerows(records)
        outfile.close()    


if __name__ == '__main__':
    args = parser.parse_args()

    if args.indir:
        assert (args.outdir is not None)
        if not os.path.exists(args.outdir):
            os.makedirs(args.outdir)
        extract_timings(args.indir, args.outdir)

    if args.monitordir:
        assert (args.monitoroutdir is not None)
        if not os.path.exists(args.monitoroutdir):
            os.makedirs(args.monitoroutdir)
        extract_monitors(args.monitordir, args.monitoroutdir)

