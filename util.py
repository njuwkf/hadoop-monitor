#!usr/bin/python
# -*- coding: utf-8 -*-

#得到jobid
import os
import time
import traceback

from data import Job


def get_jobid_by_attempid(attempt_id):
        try:
                last_ = attempt_id.find('_')
                last_ = attempt_id.find('_', last_+1)
                last_ = attempt_id.find('_', last_+1)
                return attempt_id[8:last_]
        except:
                traceback.print_exc()
                return None


#添加记录
def add_record(rec, d):
        try:
                attempt_id = rec['attempt']
                job_id = get_jobid_by_attempid(attempt_id)
                if job_id == None:
                        return
                cmd = rec['cmd']
                starttime = rec['start']
                pid = rec['pid']
                exename = os.path.basename(cmd[0]) if cmd else "None"
                rss = rec['rss']/(1024*1024)
                vms = rec['vms']/(1024*1024)
                cpu = rec['cpu']
                current = rec['current']
                host = rec['host']
                jobobj = d.get(job_id)
                if not jobobj:
                        jobobj = Job(job_id, d)
                        jobobj.set_start_time(starttime)
                        d[job_id] = jobobj
                attempt = jobobj.get(attempt_id, host)
                exe = attempt.get(pid, exename)
                seqt = exe.get('t')
                # update process info
                if jobobj.getseq('c').dict.get(current) == None:
                        jobobj.getseq('c').dict[current] = 0
                        jobobj.getseq('r').dict[current] = 0
                        jobobj.getseq('v').dict[current] = 0
                if not current in seqt.vs:
                        seqt.append_time(current)
                        jobobj.getseq('c').dict.update({current: cpu})
                jobobj.getseq('c').dict.update({current: cpu + jobobj.getseq('c').dict[current]})
                jobobj.getseq('r').dict.update({current: rss + jobobj.getseq('r').dict[current]})
                jobobj.getseq('v').dict.update({current: vms + jobobj.getseq('v').dict[current]})
                exe.get('c').dict.update({current: cpu})
                exe.get('r').dict.update({current: rss})
                exe.get('v').dict.update({current: vms})
                exe.get('c').vs = sorted(exe.get('c').dict.items(), key=lambda item: item[0])
                exe.get('r').vs = sorted(exe.get('r').dict.items(), key=lambda item: item[0])
                exe.get('v').vs = sorted(exe.get('v').dict.items(), key=lambda item: item[0])
                jobobj.getseq('c').vs = sorted(jobobj.getseq('c').dict.items(), key=lambda item: item[0])
                jobobj.getseq('r').vs = sorted(jobobj.getseq('r').dict.items(), key=lambda item: item[0])
                jobobj.getseq('v').vs = sorted(jobobj.getseq('v').dict.items(), key=lambda item: item[0])
        except:
                traceback.print_exc()

#字符串型时间
def time_to_string(t, full=False):
        return time.strftime("%Y-%m-%d %H:%M:%S" if full else "%H:%M:%S", time.localtime(t))