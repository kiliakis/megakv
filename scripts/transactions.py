import matplotlib.pyplot as plt
import matplotlib
import numpy as np
import os
import sys
# from plot.plotting_utilities import *
import argparse
import re
import bisect
# this_directory = os.path.dirname(os.path.realpath(__file__)) + "/"
this_directory = os.getcwd()
this_filename = sys.argv[0].split('/')[-1]

project_dir = this_directory

parser = argparse.ArgumentParser(description='Transactions x Time (+ Num of trans).',
                                 usage='python script.py -i results/csv -o results/plots'.format(this_filename))

parser.add_argument('-i', '--inputdir', type=str, default=os.path.join(project_dir, 'results/csv'),
                    help='The directory with the csvs.')

parser.add_argument('-o', '--outdir', type=str, default=None,
                    help='The directory to store the plots.'
                    'Default: In a plots directory inside the input results directory.')
parser.add_argument('-db', '--db', type=str, choices=['leveldb', 'megakv'], default='leveldb',
                    help='Are the results coming from leveldb or megakv.')


parser.add_argument('-s', '--show', action='store_true',
                    help='Show the plots.')

parser.add_argument('-t', '--time', type=int, default=60,
                    help='Time period in secodns to show in the x-axis. Default: 60')

args = parser.parse_args()

res_dir = args.inputdir
if args.outdir is None:
    images_dir = os.path.join(res_dir, 'plots')
else:
    images_dir = args.outdir

if not os.path.exists(images_dir):
    os.makedirs(images_dir)

gconfig = {
    'x_name': 'Time',
    'y1color': 'xkcd:blue',
    'y2color': 'xkcd:orange',
    'y1lines': {
        'SrcJ': {'ls': '-', 'lw': 1.2, 'marker': 'x', 'ms': 5, 'color': 'xkcd:blue', 'label': 'Srch'},
        'InsJ': {'ls': '-', 'lw': 1.2, 'marker': '*', 'ms': 5, 'color': 'xkcd:red', 'label': 'Insrt'},
        'SrcInsJ': {'ls': '-', 'lw': 1.2, 'marker': 'o', 'ms': 3, 'color': 'black', 'label': 'Srch+Insrt'},
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
    # 'xpoints':
    'title': {
        # 's': '',
        'fontsize': 9,
        'y': 0.96,
        'x': 0.72,
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
        'loc': 'upper right', 'ncol': 3, 'handlelength': 1.2, 'fancybox': True,
        'framealpha': 0., 'fontsize': 9, 'labelspacing': 0, 'borderpad': 0.5,
        'handletextpad': 0.2, 'borderaxespad': 0.1, 'columnspacing': 0.4,
        'bbox_to_anchor': (0, 1.15)
    },
    'subplots_adjust': {
        'wspace': 0.0, 'hspace': 0.1, 'top': 0.93
    },
    'tick_params': {
        'pad': 1, 'top': 0, 'bottom': 1, 'left': 1,
        'direction': 'out', 'length': 3, 'width': 1,
    },
    'fontname': 'DejaVu Sans Mono',
    # 'ylim': [10, 10000],
    # 'xlim': [0, 56],
    # 'yticks2': [0, 20, 40, 60, 80, 100],
    'outfiles': ['{}/{}-k{}-v{}-g{}-s{}.png',
                 # '{}/{}-{}.pdf'
                 ],
    'leveldb': {
        'yticks': [1, 10, 100, 1000, 10000],
        # 'ylim': [1, 10000]
        'ylim': [1, 10000]
    },
    'megakv': {
        'yticks': [1, 10, 100, 1000, 10000],
        # 'ylim': [10, 10000],
        'ylim': [11, 10000],
    }

}

plt.rcParams['ps.useafm'] = True
plt.rcParams['pdf.use14corefonts'] = True
plt.rcParams['text.usetex'] = True  # Let TeX do the typsetting
# Force sans-serif math mode (for axes labels)
plt.rcParams['text.latex.preamble'] = r'\usepackage{sansmath}'
# plt.rcParams['font.family'] = 'sans-serif'  # ... for regular text
# plt.rcParams['font.sans-serif'] = 'Helvetica'
# 'Helvetica, Avant Garde, Computer Modern Sans serif' # Choose a nice font here

plt.rcParams['font.family'] = gconfig['fontname']
# plt.rcParams['text.usetex'] = True

titlereg = r'k(\d+)-v(\d+)-g(\d+)-s(\d+)\.csv'

if __name__ == '__main__':
    titlereg = re.compile(titlereg)
    # one plot per input file
    for infilename in os.listdir(args.inputdir):
        match = titlereg.search(infilename)
        if match is None:
            continue

        key_len, value_len, getpercent, setpercent = match.groups()
        key_len, value_len = int(key_len), int(value_len)
        # kvarg = infilename.split('KVSIZE')[1].split('-')[0]
        # key_len, value_len = kvsize[int(kvarg)]
        # getpercent = int(infilename.split('GET')[1].split('.csv')[0])
        # setpercent = 100 - getpercent

        fullinfilename = os.path.join(args.inputdir, infilename)
        data = np.genfromtxt(fullinfilename, delimiter='\t', dtype=float,
                             skip_header=1, names=True)
        header, data = list(data[0]), data[1:]
        # I need to extract the srch, ins, srcins bws
        # as well as time and number of search and ins trans
        # plots_dir = {}
        for key in gconfig['cumsum']:
            data[key] = np.cumsum(data[key])
        x = data[gconfig['x_name']]
        x /= 1e6
        keep_points = bisect.bisect(x, args.time)
        x = x[:keep_points]
        # sys.exit()
        fig, ax = plt.subplots(ncols=1, nrows=1,
                               sharex=True, sharey=True,
                               figsize=gconfig['figsize'])

        title = rf'Key-Val:{key_len}-{value_len}, Get-Set:{getpercent}\%-{setpercent}\%'

        plt.title(title, **gconfig['title'])
        
        # ax2 = ax.twinx()
        # first ax1
        plt.sca(ax)

        plt.yscale('log', basey=10, subsy=[2, 3, 4, 5, 6, 7, 8, 9])

        for yname, yconfig in gconfig['y1lines'].items():
            if getpercent == 0 and 'SrcJ' in yname:
                continue
            elif setpercent == 0 and 'InsJ' in yname:
                continue
            if yname == 'SrcInsJ':
                y = (data['SrcJ'] + data['InsJ'])[:keep_points] / 1e6
            else:
                y = data[yname][:keep_points] / 1e6
            # x = data[gconfig['x_name']][:keep_points]
            print(f'[{yname}] min: {np.min(y)}, max: {np.max(y)}')
            plt.plot(x, y, label=yconfig['label'], color=yconfig['color'],
                     lw=yconfig['lw'], ls=yconfig['ls'],
                     marker=yconfig['marker'], ms=yconfig['ms'])
        
        plt.grid(True, which='major', alpha=0.5)
        plt.grid(False, which='major', axis='x')
        plt.grid(True, which='minor', axis='y', alpha=0.5)
        # plt.grid(True, which='both', ls='-')
        plt.gca().set_axisbelow(True)
        locmin = matplotlib.ticker.LogLocator(base=10.0,subs=(0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9), numticks=12)
        ax.yaxis.set_minor_locator(locmin)

        plt.ylabel(**gconfig['y1label'])
        plt.xlabel(**gconfig['xlabel'])
        # plt.xlim(gconfig['xlim'])
        plt.xlim([0, args.time+2])
        plt.ylim(gconfig[args.db]['ylim'])
        plt.yticks(gconfig[args.db]['yticks'])
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
            fig.savefig(file, dpi=600, bbox_inches='tight')
        if args.show:
            plt.show()
        plt.close()
