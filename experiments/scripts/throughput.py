import matplotlib.pyplot as plt
import numpy as np
import os
import sys
# from plot.plotting_utilities import *
import argparse
import re

# this_directory = os.path.dirname(os.path.realpath(__file__)) + "/"
this_directory = os.getcwd()
this_filename = sys.argv[0].split('/')[-1]

project_dir = this_directory

parser = argparse.ArgumentParser(description='Througput x Time.',
                                 usage='python script.py -i results/csv -o results/plots'.format(this_filename))

parser.add_argument('-i', '--inputdir', type=str, default=os.path.join(project_dir, 'results/csv'),
                    help='The directory with the csvs.')

parser.add_argument('-o', '--outdir', type=str, default=None,
                    help='The directory to store the plots.'
                    'Default: In a plots directory inside the input results directory.')

# parser.add_argument('-c', '--cases', type=str, default='lhc,sps,ps',
#                     help='A comma separated list of the testcases to run. Default: lhc,sps,ps')

parser.add_argument('-s', '--show', action='store_true',
                    help='Show the plots.')


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
        'SrcBW': {'ls': '-', 'lw': 1.2, 'marker': 'x', 'ms': 5, 'color': 'xkcd:blue', 'label': 'Srch'},
        'InsBW': {'ls': '-', 'lw': 1.2, 'marker': '*', 'ms': 5, 'color': 'xkcd:red', 'label': 'Insrt'},
        'SrcInsBW': {'ls': '-', 'lw': 1.2, 'marker': 'o', 'ms': 3, 'color': 'black', 'label': 'Srch+Insrt'},
    },
    'y2lines': {
        'SrcJ': {'ls': '-', 'lw': 1.5, 'marker': 'o', 'ms': 4, 'color': 'xkcd:orange', 'label': 'SrchTx'},
        'InsJ': {'ls': '-', 'lw': 1.5, 'marker': 's', 'ms': 4, 'color': 'xkcd:orange', 'label': 'InsrtTx'},
        # 'SrcInsJ': {'ls': '-', 'lw': 1.5, 'marker': '*', 'ms': 4, 'color': 'xkcd:orange', 'label': 'SrchInsrtTx'},
    },
    'cumsum': ['Time', 'SrcJ', 'InsJ'],
    'xlabel': {
        'xlabel': r'Time (s)',
        'fontsize': 10,
        'labelpad': 3,
    },
    'y1label': {
        'ylabel': r'Througput (MB/s)',
        'fontsize': 10,
        'labelpad': 3,
        # 'color': 'xkcd:blue',
    },
    'y2label': {
        'ylabel': r'Transactions',
        'fontsize': 10,
        'labelpad': 3,
        'color': 'xkcd:orange',
    },

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
    'ylim': [7, 1600],
    'xlim': [0, 56],
    'yticks': [0, 100, 200, 300, 400, 500, 600, 700],
    # 'yticks2': [0, 20, 40, 60, 80, 100],
    'outfiles': ['{}/{}-k{}-v{}-g{}-s{}.png',
                 # '{}/{}-{}.pdf'
                 ],

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

        # sys.exit()
        fig, ax = plt.subplots(ncols=1, nrows=1,
                               sharex=True, sharey=True,
                               figsize=gconfig['figsize'])

        title = rf'Key-Val:{key_len}-{value_len}, Get-Set:{getpercent}\%-{setpercent}\%'

        plt.title(title, **gconfig['title'])

        # ax2 = ax.twinx()
        # first ax1
        plt.sca(ax)
        plt.yscale('log', basey=10)
        for yname, yconfig in gconfig['y1lines'].items():
            if yname == 'SrcInsJ':
                y = data['SrcJ'] + data['InsJ']
            else:
                y = data[yname]
            x = data[gconfig['x_name']]
            print(f'[{yname}] min: {np.min(y)}, max: {np.max(y)}')

            plt.plot(x, y, label=yconfig['label'], color=yconfig['color'],
                     lw=yconfig['lw'], ls=yconfig['ls'],
                     marker=yconfig['marker'], ms=yconfig['ms'])

        plt.grid(True, which='major', alpha=0.5)
        plt.grid(False, which='major', axis='x')
        plt.grid(True, which='minor', axis='y', alpha=0.5)
        plt.gca().set_axisbelow(True)

        plt.ylabel(**gconfig['y1label'])
        plt.xlabel(**gconfig['xlabel'])
        plt.xlim(gconfig['xlim'])
        plt.ylim(gconfig['ylim'])
        # plt.yticks(gconfig['yticks'])
        ax.tick_params(**gconfig['tick_params'])
        # ax.tick_params(axis='y', labelcolor=gconfig['y1color'])

        gconfig['legend']['loc'] = 'upper left'
        plt.legend(**gconfig['legend'])

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
