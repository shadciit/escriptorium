from enum import Enum
from fabric import Connection
import os
import uuid

class State(Enum):
    IDLE = 1
    RUNNING = 2
    COMPLETE = 3

class ClusterJob:

    slurm_segmenter_train_file = 'segtrain_gpu_sub.sh'
    slurm_recognizer_train_file = 'train_gpu_sub.sh'

    def __init__(self, username, cluster_addr, workdir):
        self.username = username
        self.cluster_addr = cluster_addr
        self.workdir = workdir
        self.state = State.IDLE
        self.jobid = ''
        self.jobdir = str(uuid.uuid4())
        connect_kwargs = {
            'passphrase': os.getenv('SSH_PASSPHRASE')
        }
        self.c = Connection(host=self.cluster_addr, 
                            user=self.username,
                            connect_kwargs=connect_kwargs)

    def __del__(self):
        self.reset()
        #pass

    def erase_remote_files(self):
        with self.c.cd(self.workdir):
            try:
                #self.c.run('rm *.mlmodel *.out *.zip dataset/*', hide=True)
                #self.c.run('rmdir dataset')
                self.c.run('rm -r '+self.jobdir, hide=True)
            except:
                print("No remote file to clean")

    def request_training(self, gt_path, slurm_file):
        if self.state == State.IDLE:
            self.erase_remote_files()
            gt_filename = gt_path.split('/')[-1]
            print(gt_path)
            print(gt_filename)
            print('Uploading data ...')
            self.c.run('mkdir '+self.workdir+'/'+self.jobdir, hide=True)
            self.c.put(gt_path, self.workdir+'/'+self.jobdir+'/'+gt_filename)
            print('Done uploading data')
            os.remove(gt_path)
            with self.c.cd(self.workdir+'/'+self.jobdir):
                print('Extracting data ...')
                self.c.run('unzip '+gt_filename+' -d dataset', hide=True)
                print('Done extracting data')
                self.c.run('cp ../'+slurm_file+' .', hide=True)
                res = self.c.run('sbatch '+slurm_file, hide=True)
                self.jobid = res.stdout.split()[-1]
                print('Running job '+self.jobid)
            self.state = State.RUNNING
            return self.jobid

    def request_segmenter_training(self, gt_path):
        return self.request_training(gt_path, self.slurm_segmenter_train_file)

    def request_recognizer_training(self, gt_path):
        return self.request_training(gt_path, self.slurm_recognizer_train_file)
            

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
            self.c.get(self.workdir+'/'+self.jobdir+'/train_output_best.mlmodel', '/tmp/train_output_best.mlmodel')
            return '/tmp/train_output_best.mlmodel'
        return ''

    def best_accuracy(self):
        if self.state == State.COMPLETE:
            self.c.get(self.workdir+'/'+self.jobdir+'/'+self.jobid+'.out', '/tmp/'+self.jobid+'.out')
            with open('/tmp/'+self.jobid+'.out', 'r') as f:
                for line in f:
                    pass
                return float(line.split('(')[1].split(')')[0])
        return -1.0

    def reset(self):
        if self.state == State.COMPLETE:
            os.remove('/tmp/train_output_best.mlmodel')
        # add case for other states (kill the job if running for example)
        self.erase_remote_files()
        self.jobid = ''
        self.state = State.IDLE

    def current_state(self):
        if self.state == State.RUNNING :
            res = self.c.run('squeue --job '+self.jobid, hide=True)
            if len(res.stdout.split('\n')) == 2:
                self.state = State.COMPLETE
                return "Finished"
            state = res.stdout.split('\n')[1].split()[4]
            return state
        return "None"
