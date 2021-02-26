import matplotlib.pyplot as plt
import numpy as np
import os
import sys
from plot.plotting_utilities import *
import argparse
import re

# I need to generate these plots:
# a throughput over time
# latency over time
# Number of transactions over time
# Maybe add the num of transactions in a secondary axis
# so 2 plots, throughput, time, trans
# latency (ins/search), time, trans(ins/search)

# this_directory = os.path.dirname(os.path.realpath(__file__)) + "/"
this_directory = os.getcwd()
this_filename = sys.argv[0].split('/')[-1]

project_dir = this_directory

parser = argparse.ArgumentParser(description='Througput x Time (+ Num of trans).',
                                 usage='python script.py -i results/'.format(this_filename))

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
        'SrcBW': {'ls': '-', 'lw': 1.5, 'marker': 'o', 'ms': 4, 'color': 'xkcd:blue', 'label': 'SrchBW'},
        'InsBW': {'ls': '-', 'lw': 1.5, 'marker': 's', 'ms': 4, 'color': 'xkcd:blue', 'label': 'InsrtBW'},
        # 'SrcInsBW': {'ls': '-', 'lw': 1.5, 'marker': '*', 'ms': 4, 'color': 'xkcd:blue', 'label': 'SrchInsrtBW'},
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
        'color': 'xkcd:blue',
    },
    'y2label': {
        'ylabel': r'Transactions',
        'fontsize': 10,
        'labelpad': 3,
        'color': 'xkcd:orange',
    },

    'title': {
        # 's': '',
        'fontsize': 10,
        'y': 1,
        # 'x': 0.55,
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
        'framealpha': 0., 'fontsize': 8.5, 'labelspacing': 0, 'borderpad': 0.5,
        'handletextpad': 0.2, 'borderaxespad': 0.1, 'columnspacing': 0.4,
        # 'bbox_to_anchor': (1, 1.17)
    },
    'subplots_adjust': {
        'wspace': 0.0, 'hspace': 0.1, 'top': 0.93
    },
    'tick_params': {
        'pad': 1, 'top': 0, 'bottom': 0, 'left': 1,
        'direction': 'out', 'length': 3, 'width': 1,
    },
    'fontname': 'DejaVu Sans Mono',
    'ylim': [0., 1.15],
    'xlim': [0, 56],
    'yticks': [0.2, 0.4, 0.6, 0.8, 1],
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
        if match == None:
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

        title = rf'Key-Val: {key_len} - {value_len}, Get-Set: {getpercent}\% - {setpercent}\%'

        plt.title(title, **gconfig['title'])
        
        ax2 = ax.twinx()
        # first ax1
        plt.sca(ax)
        for yname, yconfig in gconfig['y1lines'].items():
            if yname == 'SrcInsJ':
                y = data['SrcJ'] + data['InsJ']
            else:
                y = data[yname]
            x = data[gconfig['x_name']]
            plt.plot(x, y, label=yconfig['label'], color=yconfig['color'],
                     lw=yconfig['lw'], ls=yconfig['ls'],
                     marker=yconfig['marker'], ms=yconfig['ms'])

        plt.ylabel(**gconfig['y1label'])
        plt.xlabel(**gconfig['xlabel'])
        plt.xlim(gconfig['xlim'])
        ax.tick_params(**gconfig['tick_params'])
        ax.tick_params(axis='y', labelcolor=gconfig['y1color'])

        gconfig['legend']['loc'] = 'upper left'
        plt.legend(**gconfig['legend'])
        # plt.tight_layout()

        # plt.ylim(gconfig['ylim'])
        # plt.xlim(xmin=0-width, xmax=xmax-3*width/2)
        # plt.yticks(gconfig['yticks'], **gconfig['ticks'])
        # plt.xticks(np.arange(len(xref)), np.array(xref, int), **gconfig['xticks'])

        # then ax2
        plt.sca(ax2)
        for yname, yconfig in gconfig['y2lines'].items():
            if yname == 'SrcInsJ':
                y = data['SrcJ'] + data['InsJ']
            else:
                y = data[yname]
            x = data[gconfig['x_name']]
            plt.plot(x, y, label=yconfig['label'], color=yconfig['color'],
                     lw=yconfig['lw'], ls=yconfig['ls'],
                     marker=yconfig['marker'], ms=yconfig['ms'])

        plt.ylabel(**gconfig['y2label'])
        plt.xlabel(**gconfig['xlabel'])
        plt.xlim(gconfig['xlim'])
        ax.tick_params(**gconfig['tick_params'])
        ax2.tick_params(axis='y', labelcolor=gconfig['y2color'])
        gconfig['legend']['loc'] = 'upper right'
        plt.legend(**gconfig['legend'])
        # plt.tight_layout()


        fig.tight_layout()

        for file in gconfig['outfiles']:
            file = file.format(
                images_dir, this_filename[:-3], key_len, value_len, getpercent, setpercent)
            print('[{}] {}: {}'.format(this_filename[:-3], 'Saving figure', file))
            save_and_crop(fig, file, dpi=600, bbox_inches='tight')
        if args.show:
            plt.show()
        plt.close()

    # pos = 0
    # step = 1.
    # labels = set()
    # avg = {}
    # xticks = []
    # xtickspos = []
    # for col, case in enumerate(args.cases):
    #     print('[{}] tc: {}: {}'.format(
    #         this_filename[:-3], case, 'Reading data'))
    #     plots_dir = {}
    #     for file in gconfig['files']:
    #         file = file.format(res_dir, case)
    #         # print(file)
    #         data = np.genfromtxt(file, delimiter='\t', dtype=str)
    #         header, data = list(data[0]), data[1:]
    #         temp = get_plots(header, data, gconfig['lines'],
    #                          exclude=gconfig.get('exclude', []),
    #                          prefix=True)
    #         for key in temp.keys():
    #             if 'tp-approx' in file:
    #                 plots_dir['_{}_tp1'.format(key)] = temp[key].copy()
    #             else:
    #                 plots_dir['_{}_tp0'.format(key)] = temp[key].copy()

    #     width = step / (len(plots_dir.keys()))

    #     # First the reference value
    #     keyref = ''
    #     for k in plots_dir.keys():
    #         if 'approx0' in k and 'double' in k:
    #             keyref = k
    #             break
    #     if keyref == '':
    #         print('ERROR: reference key not found')
    #         exit(-1)

    #     refvals = plots_dir[keyref]

    #     xref = get_values(refvals, header, gconfig['x_name'])
    #     omp = get_values(refvals, header, gconfig['omp_name'])
    #     y = get_values(refvals, header, gconfig['y_name'])
    #     parts = get_values(refvals, header, 'ppb')
    #     bunches = get_values(refvals, header, 'b')
    #     turns = get_values(refvals, header, 't')
    #     yref = parts * bunches * turns / y

    #     print('[{}] tc: {}: {}'.format(
    #         this_filename[:-3], case, 'Plotting data'))
    #     # To sort the keys, by approx and then reduce value
    #     print(plots_dir.keys())
    #     keys = ['_'.join(a.split('_')[1:4]) for a in list(plots_dir.keys())]
    #     print(keys)
    #     keys = np.array(list(plots_dir.keys()))[np.argsort(keys)]
    #     idx = 0
    #     for k in keys:
    #         values = plots_dir[k]
    #         # mpiv = k.split('_mpi')[1].split('_')[0]
    #         # lb = k.split('lb')[1].split('_')[0]
    #         approx = k.split('approx')[1].split('_')[0]
    #         # tp = k.split('_')[-1]
    #         red = k.split('red')[1].split('_')[0]
    #         experiment = k.split('_')[-1]
    #         prec = k.split('prec')[1].split('_')[0]
    #         # if lb == 'interval':
    #         #     lb = 'LB-'
    #         # elif lb == 'reportonly':
    #         #     lb = ''
    #         # if tp == 'tp1':
    #         #     tp = 'TP-'
    #         # elif tp == 'tp0':
    #         #     tp = ''
    #         approx = gconfig['approx'][approx]
    #         label = gconfig['label'][prec+approx]
    #         # if prec == 'single':
    #         #     label = 'f32'
    #         # if approx == '':
    #         #     label = 'base'
    #         # elif approx == 'RDS':
    #         #     label += 'RDS'
    #         # elif approx == 'SRP':
    #         #     label += 'SRP-{}'.format(red)
    #         if approx == 'SRP':
    #             label += '-{}'.format(red)
    #         if label == 'base':
    #             continue

    #         # if label == '1':
    #         #     label = 'base'
    #         # if label[-1] == '-':
    #         #     label = label[:-1]

    #         x = get_values(values, header, gconfig['x_name'])
    #         omp = get_values(values, header, gconfig['omp_name'])
    #         y = get_values(values, header, gconfig['y_name'])
    #         parts = get_values(values, header, 'ppb')
    #         bunches = get_values(values, header, 'b')
    #         turns = get_values(values, header, 't')

    #         # This is the throughput
    #         y = parts * bunches * turns / y

    #         speedup = []
    #         j = 0
    #         for i, xiref in enumerate(xref):
    #             if j < len(x) and xiref == x[j]:
    #                 speedup.append(yref[i]/y[j])
    #                 j += 1
    #             else:
    #                 speedup.append(0)
    #         speedup = np.array(speedup)
    #         # speedup = yref / y
    #         # x_new = []
    #         # sp_new = []
    #         # for i, xi in enumerate(gconfig['x_to_keep']):
    #         #     x_new.append(xi)
    #         #     if xi in x:
    #         #         sp_new.append(speedup[list(x).index(xi)])
    #         #     else:
    #         #         sp_new.append(0)
    #         # x = np.array(x_new)
    #         # speedup = np.array(sp_new)
    #         # efficiency = 100 * speedup / (x * omp[0] / ompref)
    #         x = xref * omp[0]

    #         # width = .9 * step / (len(x))
    #         if label not in avg:
    #             avg[label] = []
    #         avg[label].append(speedup)
    #         # efficiency = 100 * speedup / x
    #         if label in labels:
    #             label = None
    #         else:
    #             labels.add(label)
    #         plt.bar(pos + idx*width + np.arange(len(speedup)), speedup, width=0.9*width,
    #                 edgecolor='0.', label=label, hatch=gconfig['hatches'][idx],
    #                 color=gconfig['colors'][idx])
    #         if k != keyref:
    #             for i in np.arange(len(speedup)):
    #                 ax.annotate('{:.2f}'.format(speedup[i]),
    #                             xy=(pos+idx*width+i, speedup[i]),
    #                             rotation='90', **gconfig['annotate'])
    #         idx += 1
    #     pos += step

    # # vals = np.mean(avg, axis=0)
    # # for idx, key in enumerate(avg.keys()):
    # #     vals = avg[key]
    # #     val = np.mean(vals)
    # #     plt.bar(pos + idx*width, val, width=0.9*width,
    # #             edgecolor='0.', label=None, hatch=gconfig['hatches'][idx],
    # #             color=gconfig['colors'][idx])
    # #     text = '{:.2f}'.format(val)
    # #     if idx == 0:
    # #         text = ''
    # #     else:
    # #         text = text[:]
    # #     ax.annotate(text, xy=(pos + idx*width, 0.01 + val),
    # #                 rotation='90',
    # #                 **gconfig['annotate'])
    # # pos += step

    # plt.ylim(gconfig['ylim'])
    # handles, labels = ax.get_legend_handles_labels()
    # # print(labels)

    # plt.legend(handles=handles, labels=labels, **gconfig['legend'])
    # _, xmax = plt.xlim()
    # plt.xlim(xmin=0-width, xmax=xmax-3*width/2)
    # plt.yticks(gconfig['yticks'], **gconfig['ticks'])

    # plt.xticks(np.arange(len(xref)), np.array(xref, int), **gconfig['xticks'])
    # plt.xlabel(**gconfig['xlabel'])
    # # plt.xticks(np.arange(pos) + step/2,
    # #            [c.upper() for c in args.cases] + ['AVG'], **gconfig['xticks'])

    # ax.tick_params(**gconfig['tick_params'])
    # plt.tight_layout()
    # # plt.subplots_adjust(**gconfig['subplots_adjust'])
    # for file in gconfig['outfiles']:
    #     file = file.format(
    #         images_dir, this_filename[:-3], '-'.join(args.cases))
    #     print('[{}] {}: {}'.format(this_filename[:-3], 'Saving figure', file))
    #     save_and_crop(fig, file, dpi=600, bbox_inches='tight')
    # if args.show:
    #     plt.show()
    # plt.close()
