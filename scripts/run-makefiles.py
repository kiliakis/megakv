import subprocess
import os
import sys
# from datetime import datetime
import time
import random
# import yaml
import argparse
import numpy as np

# import common

this_directory = os.getcwd()
# this_directory = os.path.dirname(os.path.realpath(__file__)) + "/"
# this_filename = sys.argv[0].split('/')[-1]

parser = argparse.ArgumentParser(description='Run the experiments.',
                                 usage='python script.py -s srcdir -i indir -o outdir -t timeout')

# parser.add_argument('-e', '--environment', type=str, default='local', choices=['local', 'slurm', 'condor'],
#                     help='The environment to run the scan.')

# parser.add_argument('-t', '--testcases', type=str, default=['lhc,sps,ps'],
#                     help='Which testcases to run. Default: all')
parser.add_argument('-s', '--srcdir', type=str, default=os.path.join(this_directory, 'src'),
                    help='The directory that contains the src code.')

parser.add_argument('-i', '--indir', type=str, default='./experiments/makefiles',
                    help='Input directory with the makefiles to run.')

parser.add_argument('-o', '--outdir', type=str, default='./results',
                    help='Output directory to store the output data. Default: ./results')
parser.add_argument('-t', '--timeout', type=int, default=60,
                    help='Time interval of each run in seconds. ')

parser.add_argument('-n', '--total_sims', type=int, default=-1,
                    help='How many to run. Default: -1 (run all)')


if __name__ == '__main__':
    args = parser.parse_args()
    srcdir = args.srcdir
    exe = os.path.join(srcdir, 'build/megakv')

    outdir = args.outdir
    compiledir = os.path.join(outdir, 'compile')
    rundir = os.path.join(outdir, 'run')
    monitordir = os.path.join(outdir, 'monitor')

    if not os.path.exists(compiledir):
        os.makedirs(compiledir)
    if not os.path.exists(rundir):
        os.makedirs(rundir)
    if not os.path.exists(monitordir):
        os.makedirs(monitordir)

    # iterate over the makefiles
    allmkfiles = os.listdir(args.indir)
    total_sims = args.total_sims
    if total_sims < 0:
        total_sims = len(allmkfiles)
    current_sim = 0
    for mkfile in allmkfiles:
        if total_sims <= 0:
            break
        absmkfile = os.path.join(args.indir, mkfile)
        plainmkfile = (mkfile.split('/')[-1]).replace('Makefile_', '')
        out = open(os.path.join(compiledir, f'{plainmkfile}.txt'), 'w')
        out.write(f'{absmkfile}\n')
        cmd = f'cp {absmkfile} {os.path.join(srcdir, "Makefile")}'
        # print(cmd)
        subprocess.run(cmd, shell=True,
                       stdout=out,
                       stderr=out)
        cmd = f'make -C {srcdir}'
        # print(cmd)
        subprocess.run(cmd, shell=True,
                       stdout=out,
                       stderr=out,
                       env=os.environ.copy())
        # cmd = f'rm {os.path.join(srcdir, plainmkfile)}'
        # subprocess.run(cmd, shell=True,
        #                 stdout=out,
        #                 stderr=out)
        out.close()

        runout = open(os.path.join(rundir, f'{plainmkfile}.txt'), 'w')
        monitorout = open(os.path.join(monitordir, f'{plainmkfile}.txt'), 'w')
        subp = subprocess.Popen([exe],
                                # timeout=args.timeout,
                                stdout=runout,
                                stderr=runout,
                                env=os.environ.copy())
        monitorp = subprocess.Popen(['nvidia-smi', 'dmon', '-o', 'T'],
                                stdout=monitorout,
                                stderr=monitorout)
        time.sleep(args.timeout)
        os.kill(subp.monitorp, 1)
        os.kill(subp.pid, 1)
        # while 1:
        #     if (time.time() - p.create_time()) > TIMEOUT:
        #         p.kill()
        #         raise RuntimeError('timeout')
        #     time.sleep(5)
        runout.close()
        total_sims -= 1
        current_sim += 1
        print("%lf %% is completed" % (100.0 * current_sim
                                       / len(allmkfiles)))

    # os.environ['BLONDHOME'] = common.blond_home
    # # os.environ['FFTWDIR'] = os.environ.get('FFTWDIR', '$HOME/install')
    # # os.environ['HOME'] =
    # for tc in args.testcases.split(','):
    #     yc = yaml.load(open(this_directory + '/{}_configs.yml'.format(tc), 'r'),
    #                    Loader=yaml.FullLoader)[args.environment]

    #     result_dir = top_result_dir + '/{}/{}/{}/{}/{}'

    #     job_name_form = '_p{}_b{}_s{}_t{}_w{}_o{}_N{}_red{}_mtw{}_seed{}_approx{}_mpi{}_lb{}_monitor{}_tp{}_prec{}_artdel{}_gpu{}_'

    #     total_sims = 0
    #     for rc in yc['run_configs']:
    #         maxlen = np.max([len(v) if isinstance(v, list)
    #                          else 1 for k, v in yc['configs'][rc].items()])
    #         for k, v in yc['configs'][rc].items():
    #             if isinstance(v, list):
    #                 assert maxlen % len(
    #                     v) == 0, 'Size of {} must be a multiple of {}'.format(len(v), maxlen)
    #                 yc['configs'][rc][k] = v * int(maxlen / len(v))
    #             else:
    #                 yc['configs'][rc][k] = [v] * maxlen
    #         total_sims += np.sum(yc['configs'][rc]['repeats'])

    #     print("Total runs: ", total_sims)
    #     current_sim = 0

    #     for analysis in yc['run_configs']:
    #         # For the extract script

    #         config = yc['configs'][analysis]
    #         # make the size of all lists equal

    #         ps = config['particles']
    #         bs = config['bunches']
    #         ss = config['slices']
    #         ts = config['turns']
    #         ws = config['workers']
    #         oss = config['omp']
    #         rs = config['reduce']
    #         exes = config['exe']
    #         times = config['time']
    #         # partitions = config['partition']
    #         mtws = config.get('mtw', ['0']*len(ps))
    #         ms = config.get('monitor', ['0']*len(ps))
    #         seeds = config.get('seed', ['0']*len(ps))
    #         approxs = config['approx']
    #         timings = config['timing']
    #         mpis = config['mpi']
    #         logs = config['log']
    #         lbs = config['loadbalance']
    #         repeats = config['repeats']
    #         tps = config['withtp']
    #         precs = config['precision']
    #         artdels = config['artificialdelay']
    #         gpus = config['gpu']

    #         nodes = config.get('nodes', [0]*len(ps))

    #         for (N, p, b, s, t, r, w, o, time,
    #              mtw, m, seed, exe, approx,
    #              timing, mpi, log, lb,
    #              tp, prec, reps, artdel, gpu) in zip(nodes, ps, bs, ss, ts, rs, ws,
    #                                                  oss, times, mtws, ms, seeds,
    #                                                  exes, approxs, timings, mpis,
    #                                                  logs, lbs, tps, precs,
    #                                                  repeats, artdels, gpus):

    #             if N == 0:
    #                 N = int(max(np.ceil(w * o / common.cores_per_cpu), 1))

    #             job_name = job_name_form.format(p, b, s, t, w, o, N,
    #                                             r, mtw, seed, approx, mpi,
    #                                             lb, m, tp, prec, artdel, gpu)

    #             for i in range(reps):
    #                 timestr = datetime.now().strftime('%d%b%y.%H-%M-%S')
    #                 timestr = timestr + '-' + str(random.randint(0, 100))
    #                 output = result_dir.format(
    #                     tc, analysis, job_name, timestr, 'output.txt')
    #                 error = result_dir.format(
    #                     tc, analysis, job_name, timestr, 'error.txt')
    #                 condor_log = result_dir.format(
    #                     tc, analysis, job_name, timestr, 'log.txt')
    #                 monitorfile = result_dir.format(
    #                     tc, analysis, job_name, timestr, 'monitor')
    #                 log_dir = result_dir.format(
    #                     tc, analysis, job_name, timestr, 'log')
    #                 report_dir = result_dir.format(
    #                     tc, analysis, job_name, timestr, 'report')
    #                 for d in [log_dir, report_dir]:
    #                     if not os.path.exists(d):
    #                         os.makedirs(d)

    #                 os.environ['OMP_NUM_THREADS'] = str(o)

    #                 analysis_file = open(os.path.join(top_result_dir, tc,
    #                                                   analysis, '.analysis'),
    #                                      'a')

    #                 exe_args = [
    #                     common.python, os.path.join(common.exe_home, exe),
    #                     '--particles='+str(int(p)),
    #                     '--slices='+str(s),
    #                     '--bunches='+str(int(b)),
    #                     '--turns='+str(t),
    #                     '--omp='+str(o),
    #                     '--seed='+str(seed),
    #                     '--time='+str(timing), '--timedir='+report_dir,
    #                     '--monitor='+str(m), '--monitorfile='+monitorfile,
    #                     '--reduce='+str(r),
    #                     '--mtw='+str(mtw),
    #                     '--precision='+str(prec),
    #                     '--approx='+str(approx),
    #                     '--loadbalance='+lb,
    #                     '--withtp='+str(tp),
    #                     '--log='+str(log), '--logdir='+log_dir,
    #                     '--artificialdelay='+str(artdel),
    #                     '--gpu='+str(gpu)]

    #                 if args.environment == 'local':
    #                     batch_args = [common.mpirun, '-n', str(w),
    #                                   '-bind-to', 'socket']
    #                     all_args = batch_args + exe_args

    #                 elif args.environment == 'slurm':
    #                     batch_args = [
    #                         common.slurm['submit'],
    #                         common.slurm['nodes'], str(N),
    #                         common.slurm['workers'], str(w),
    #                         common.slurm['tasks_per_node'], str(
    #                             int(np.ceil(w/N))),
    #                         common.slurm['cores'], str(o),  # str(o),
    #                         common.slurm['time'], str(time),
    #                         common.slurm['output'], output,
    #                         common.slurm['error'], error,
    #                         common.slurm['jobname'], tc + '-' + analysis + job_name.split('/')[0] + '-' + str(i)]
    #                     batch_args += common.slurm['default_args']
    #                     batch_args += [common.slurm['script'],
    #                                    common.slurm['run']]
    #                     all_args = batch_args + exe_args

    #                 elif args.environment == 'condor':
    #                     arg_str = '"{} -n {} '.format(common.mpirun, str(w))
    #                     arg_str = arg_str + ' '.join(exe_args) + '"'
    #                     # arg_str+= ' --version "'
    #                     batch_args = [
    #                         common.condor['submit'],
    #                         common.condor['executable'],
    #                         common.condor['arguments']+arg_str,
    #                         common.condor['cores']+str(o),  # str(o),
    #                         '-append', common.condor['time']+str(time),
    #                         common.condor['output']+output,
    #                         common.condor['error']+error,
    #                         common.condor['log']+condor_log,
    #                         common.condor['jobname'], tc + '-' + analysis + job_name.split('/')[0] + '-' + str(i)]
    #                     batch_args += common.condor['default_args']
    #                     batch_args += ['-file', common.condor['script']]
    #                     all_args = batch_args

    #                 print(job_name, timestr)
    #                 print(job_name, timestr, file=analysis_file)

    #                 all_args = ' '.join(all_args)
    #                 print(all_args, file=analysis_file)

    #                 subprocess.call(all_args,
    #                                 shell=True,
    #                                 stdout=open(output, 'w'),
    #                                 stderr=open(error, 'w'),
    #                                 env=os.environ.copy())

    #                 # sleep(5)
    #                 current_sim += 1
    #                 print("%lf %% is completed" % (100.0 * current_sim
    #                                                / total_sims))

    #                 analysis_file.close()
