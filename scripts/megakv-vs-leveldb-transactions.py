import matplotlib.pyplot as plt
import matplotlib
import numpy as np
import os
import sys
# from plot.plotting_utilities import *
import argparse
import re
import bisect
from scipy.interpolate import interp1d

# this_directory = os.path.dirname(os.path.realpath(__file__)) + "/"
this_directory = os.getcwd()
this_filename = sys.argv[0].split('/')[-1]

project_dir = this_directory

parser = argparse.ArgumentParser(description='Transactions x Time.',
                                 usage='python script.py -m megakv/csv -l leveldb/csv -o plots'.format(this_filename))

parser.add_argument('-m', '--megakvdir', type=str,
                    help='The directory with the megakv csvs.')

parser.add_argument('-l', '--leveldbdir', type=str,
                    help='The directory with the leveldb csvs.')

parser.add_argument('-o', '--outdir', type=str,
                    help='The directory to store the plots.')

parser.add_argument('-t', '--time', type=int, default=60,
                    help='Time period in secodns to show in the x-axis. Default: 60')

# parser.add_argument('-db', '--db', type=str, choices=['leveldb', 'megakv'], default='leveldb',
#                     help='Are the results coming from leveldb or megakv.')

parser.add_argument('-s', '--show', action='store_true',
                    help='Show the plots.')



gconfig = {
    'x_name': 'Time',

    'mkv-lines': {
        'SrcJ': {'ls': '-', 'lw': 1.2, 'marker': 'x', 'ms': 5, 'color': 'xkcd:light blue', 'label': 'MKV-Get'},
        'InsJ': {'ls': '-', 'lw': 1.2, 'marker': '*', 'ms': 5, 'color': 'xkcd:blue', 'label': 'MKV-Set'},
        'SrcInsJ': {'ls': '-', 'lw': 1.2, 'marker': 'o', 'ms': 3, 'color': 'xkcd:dark blue', 'label': 'MKV-Tot'},
    },
    'ldb-lines': {
        'SrcJ': {'ls': '-', 'lw': 1.2, 'marker': 'x', 'ms': 5, 'color': 'xkcd:light red', 'label': 'LDB-Get'},
        'InsJ': {'ls': '-', 'lw': 1.2, 'marker': '*', 'ms': 5, 'color': 'xkcd:red', 'label': 'LDB-Set'},
        'SrcInsJ': {'ls': '-', 'lw': 1.2, 'marker': 'o', 'ms': 3, 'color': 'xkcd:dark red', 'label': 'LDB-Tot'},
    },

    'cumsum': ['Time', 'SrcJ', 'InsJ'],
    'xlabel': {
        'xlabel': r'Time (s)',
        'fontsize': 10,
        'labelpad': 3,
    },
    'y1label': {
        'ylabel': r'Transactions (x$10^6$)',
        'fontsize': 10,
        'labelpad': 3,
        # 'color': 'xkcd:blue',
    },

    'title': {
        # 's': '',
        'fontsize': 9,
        'y': 0.96,
        # 'x': 0.5,
        # 'fontweight': 'bold',
    },
    'figsize': [5, 2.2],
    'annotate': {
        'fontsize': 8.5,
        'textcoords': 'data',
        'va': 'bottom',
        'ha': 'center'
    },
    'xticks': {'fontsize': 10, 'rotation': '0', 'fontweight': 'bold'},
    'ticks': {'fontsize': 10, 'rotation': '0'},
    'fontsize': 10,
    'legend': {
        'loc': 'upper left', 'ncol': 3, 'handlelength': 1., 'fancybox': True,
        'framealpha': .8, 'fontsize': 9, 'labelspacing': 0, 'borderpad': 0.1,
        'handletextpad': 0.1, 'borderaxespad': 0.1, 'columnspacing': 0.2,
        # 'bbox_to_anchor': (0, 1.15)
    },
    'subplots_adjust': {
        'wspace': 0.0, 'hspace': 0.1, 'top': 0.93
    },
    'tick_params': {
        'pad': 1, 'top': 0, 'bottom': 1, 'left': 1,
        'direction': 'out', 'length': 3, 'width': 1,
    },
    'fontname': 'DejaVu Sans Mono',
    'yticks': [1, 10, 100, 1000, 10000],
    'ylim': [1, 10000],

    'outfiles': ['{}/{}-k{}-v{}-g{}-s{}.png',
                 # '{}/{}-{}.pdf'
                 ],

}


plt.rcParams['ps.useafm'] = True
plt.rcParams['pdf.use14corefonts'] = True
plt.rcParams['text.usetex'] = True  # Let TeX do the typsetting
plt.rcParams['text.latex.preamble'] = r'\usepackage{sansmath}'

plt.rcParams['font.family'] = gconfig['fontname']

titlereg = r'k(\d+)-v(\d+)-g(\d+)-s(\d+)\.csv'

if __name__ == '__main__':
    args = parser.parse_args()

    images_dir = args.outdir
    if not os.path.exists(images_dir):
        os.makedirs(images_dir)

    titlereg = re.compile(titlereg)
    # one plot per input file

    # first find files present in both directories

    # megakvfiles = os.listdir(args.megakvdir)
    megakvfiles = set()
    for file in os.listdir(args.megakvdir):
        if titlereg.search(file):
            megakvfiles.add(file)

    leveldbfiles = set()
    for file in os.listdir(args.leveldbdir):
        if titlereg.search(file):
            leveldbfiles.add(file)

    infilesnames = megakvfiles & leveldbfiles
    for file in (megakvfiles ^ leveldbfiles):
        print(f'File [{file}] not found in both directories')

    for infilename in infilesnames:
        match = titlereg.search(infilename)
        if match is None:
            continue

        key_len, value_len, getpercent, setpercent = match.groups()
        key_len, value_len = int(key_len), int(value_len)
        getpercent, setpercent = int(getpercent), int(setpercent)

        # read megakv data
        fullinfilename = os.path.join(args.megakvdir, infilename)
        data = np.genfromtxt(fullinfilename, delimiter='\t', dtype=float,
                             skip_header=1, names=True)
        mkvheader, mkvdata = list(data[0]), data[1:]

        # read leveldb data
        fullinfilename = os.path.join(args.leveldbdir, infilename)
        data = np.genfromtxt(fullinfilename, delimiter='\t', dtype=float,
                             skip_header=1, names=True)
        ldbheader, ldbdata = list(data[0]), data[1:]

        for key in gconfig['cumsum']:
            mkvdata[key] = np.cumsum(mkvdata[key])
            ldbdata[key] = np.cumsum(ldbdata[key])

        mkvx = mkvdata[gconfig['x_name']] / 1e6
        ldbx = ldbdata[gconfig['x_name']] / 1e6

        # for k in ldbdata.dtype.names:
        #     if k in ['SrcBW', 'InsBW', 'SrcInsBW']:
        #         # convert to ns
        #         ldbdata[k] *= 1e6

        mkvpoints = bisect.bisect(mkvx, args.time)
        mkvx = mkvx[:mkvpoints]
        
        ldbpoints = bisect.bisect(ldbx, args.time)
        ldbx = ldbx[:ldbpoints]

        fig, ax = plt.subplots(ncols=1, nrows=1,
                               sharex=True, sharey=True,
                               figsize=gconfig['figsize'])

        title = rf'Key-Val:{key_len}-{value_len}, Get-Set:{getpercent}\%-{setpercent}\%'

        plt.title(title, **gconfig['title'])

        plt.sca(ax)
        plt.yscale('log', basey=10)
        assert (gconfig['ldb-lines'].keys() == gconfig['mkv-lines'].keys())
        
        for yname in gconfig['ldb-lines'].keys():
            mkvyconfig = gconfig['mkv-lines'][yname]
            ldbyconfig = gconfig['ldb-lines'][yname]
            if getpercent == 0 and 'Src' in yname:
                continue
            elif setpercent == 0 and 'Ins' in yname:
                continue

            if yname == 'SrcInsJ':
                mkvy = (mkvdata['SrcJ'] + mkvdata['InsJ'])[:mkvpoints] / 1e6
                ldby = (ldbdata['SrcJ'] + ldbdata['InsJ'])[:ldbpoints] / 1e6
            else:
                mkvy = mkvdata[yname][:mkvpoints] / 1e6
                ldby = ldbdata[yname][:mkvpoints] / 1e6


            print(f'[mkv-{yname}] min: {np.min(mkvy)}, max: {np.max(mkvy)}')
            print(f'[ldb-{yname}] min: {np.min(ldby)}, max: {np.max(ldby)}')

            plt.plot(mkvx, mkvy, label=mkvyconfig['label'], color=mkvyconfig['color'],
                     lw=mkvyconfig['lw'], ls=mkvyconfig['ls'],
                     marker=mkvyconfig['marker'], ms=mkvyconfig['ms'])

            plt.plot(ldbx, ldby, label=ldbyconfig['label'], color=ldbyconfig['color'],
                     lw=ldbyconfig['lw'], ls=ldbyconfig['ls'],
                     marker=ldbyconfig['marker'], ms=ldbyconfig['ms'])


        plt.grid(True, which='major', alpha=0.5)
        plt.grid(False, which='major', axis='x')
        plt.grid(True, which='minor', axis='y', alpha=0.5)
        plt.gca().set_axisbelow(True)

        plt.ylabel(**gconfig['y1label'])
        plt.xlabel(**gconfig['xlabel'])
        # plt.xlim(gconfig['xlim'])
        plt.xlim([0, args.time+2])
        plt.ylim(gconfig['ylim'])
        plt.yticks(gconfig['yticks'])
        locmin = matplotlib.ticker.LogLocator(base=10.0,subs=(0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9), numticks=12)
        ax.yaxis.set_minor_locator(locmin)

        ax.tick_params(**gconfig['tick_params'])
        # ax.tick_params(axis='y', labelcolor=gconfig['y1color'])

        gconfig['legend']['loc'] = 'upper left'
        plt.legend(**gconfig['legend'])
        # plt.tight_layout()

        fig.tight_layout()

        for file in gconfig['outfiles']:
            file = file.format(
                images_dir, this_filename[:-3], key_len, value_len, getpercent, setpercent)
            print('[{}] {}: {}'.format(this_filename[:-3], 'Saving figure', file))
            # save_and_crop(fig, file, dpi=600, bbox_inches='tight')
            fig.savefig(file, dpi=600, bbox_inches='tight')
        if args.show:
            plt.show()
        plt.close()
