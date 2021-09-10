from enum import Enum
from fabric import Connection
import os

class State(Enum):
    IDLE = 1
    RUNNING = 2
    COMPLETE = 3

class Cluster:

    slurm_file = 'ketos_gpu_sub.sh'
    result = ''
    jobid = ''

    def __init__(self, username, cluster_addr, workdir):
        self.username = username
        self.cluster_addr = cluster_addr
        self.workdir = workdir
        self.state = State.IDLE
        self.c = Connection(host=self.cluster_addr, 
                            user=self.username)

    def __del__(self):
        self.reset()

    def request_training(self, gt_path):
        if self.state == State.IDLE:
            gt_filename = gt_path.split('/')[-1]
            print(gt_path)
            print(gt_filename)
            print('Uploading data ...')
            self.c.put(gt_path, self.workdir+'/'+gt_filename)
            print('Done uploading data')
            os.remove(gt_path)
            with self.c.cd(self.workdir):
                print('Extracting data ...')
                self.c.run('unzip '+gt_filename+' -d dataset', hide=True)
                print('Done extracting data')
                res = self.c.run('sbatch '+self.slurm_file, hide=True)
                self.jobid = res.stdout.split()[-1]
                print('Running job '+self.jobid)
            self.state = State.RUNNING
            

    def task_is_complete(self):
        if self.state == State.RUNNING :
            res = self.c.run('squeue --job '+self.jobid, hide=True)
            if len(res.stdout.split('\n')) == 2:
                self.state = State.COMPLETE
                return True
            state = res.stdout.split('\n')[1].split()[4]
            print('Training state : '+state)
            return False
        return True

    def result_path(self):
        if self.state == State.COMPLETE:
            # Download result ...
            return self.result
        return ''

    def reset(self):
        if self.result != '':
            # delete file
            None
        self.state = State.IDLE