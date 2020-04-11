#!usr/bin/python
# -*- coding: utf-8 -*-

import traceback
import sys
import os
import time
import json
import logging
import web
import urllib
import cStringIO as StringIO
import matplotlib.pyplot as plt
import cPickle as pickle

#得到jobid
def get_jobid_by_attempid(attempt_id):
        try:
                last_ = attempt_id.find('_')
                last_ = attempt_id.find('_', last_+1)
                last_ = attempt_id.find('_', last_+1)
                return attempt_id[8:last_]
        except:
                traceback.print_exc()
                return None

#job类
class Job(object):
        def __init__(self, jobid, parent):
#               print "Job %s" % jobid
                self.id = jobid
                self.attempts = {}
                self.time = 0
                self.parent = parent
        def settime(self, t):
                self.time = t
        def get(self,id,host=None):
                ret = self.attempts.get(id)
                if ret == None:
                        ret = Attempt(id, host, self)
                        self.attempts[id] = ret
                return ret

#attempt类
class Attempt(object):
        def __init__(self, attemptid, host, parent):
#               print "Attempt %s" % attemptid
                self.id = attemptid
                self.exes = {}
                self.time = 0
                self.host = host
                self.parent = parent
        def settime(self, t):
                self.time = t
                self.parent.settime(t)
        def get(self,id, exe=None):
                ret = self.exes.get(id)
                if ret == None:
                        ret = Exe(id, exe, self)
                        self.exes[id] = ret
                return ret

class Exe(object):
        def __init__(self, pid, exe, parent):
#               print "Exe %s" % exe
                self.id = pid
                self.exe = exe
                self.seqs = {}
                self.time = 0
                self.parent = parent
        def settime(self, t):
                self.time = t
                self.parent.settime(t)
        def get(self,id):
                ret = self.seqs.get(id)
                if ret == None:
                        ret = Seq(id, self)
                        self.seqs[id] = ret
                return ret

class Seq(object):
        def __init__(self, name, parent):
#               print "Seq %s" % name
                self.id = name
                self.vs = []
                self.time = 0
                self.parent = parent
        def appendtime(self, t):
                self.time = t
                self.vs.append(t)
                self.parent.settime(t)

#添加记录
def add_record(rec, d):
        try:
                attempt_id = rec['attempt']
                job_id = get_jobid_by_attempid(attempt_id)
                if job_id == None:
                        return
                cmd = rec['cmd']
                pid = rec['pid']
                exename = os.path.basename(cmd.split()[0]) if cmd else "None"
                rss = rec['rss']
                vms = rec['vms']
                cpu = rec['cpu']
                current = rec['current']
                host = rec['host']
                jobobj = d.get(job_id)
                if not jobobj:
                        jobobj = Job(job_id, d)
                        d[job_id] = jobobj
                attempt = jobobj.get(attempt_id, host)
                exe = attempt.get(pid, exename)
                seqt = exe.get('t')
                seqt.appendtime(current)
                exe.get('c').vs.append(cpu)
                exe.get('r').vs.append(rss)
                exe.get('v').vs.append(vms)
        except:
                traceback.print_exc()

#字符串型时间
def time_to_string(t, full=False):
        return time.strftime("%Y-%m-%d %H:%M:%S" if full else "%H:%M:%S", time.localtime(t))


urls = (
        '/', 'jobs_view',
        '/jobs', 'jobs_view',
        '/job_([_/d]+)', 'job_view',
        '/(attempt_[^/s]+)', 'attempt_view',
        '/text/(attempt_[^/s]+)', 'attempt_text_view',
        '/fig/(attempt_[^/s]+).png', 'attempt_fig',
        '/submit', 'submit_service',
        '/save', 'save_service',
        '/load', 'load_service',
        '/clean', 'clean_service',
        )


#web.config.debug = False
app = web.application(urls,globals())
all = {} # all jobs traced

#所有任务界面（显示所有job_id和最后更新时间）
class jobs_view(object):
        def GET(self):
                out = StringIO.StringIO()
                out.write('<html><head><title>Jobs</title></head><body>')
                out.write('<h2>List of all monitoring jobs:</h2>')
                have = False
                for jobid,job in all.iteritems():
                        have = True
                        out.write('<li><a href="/job_%s" mce_href="job_%s">job_%s</a> Last Update: %s</li>' % (jobid, jobid,jobid, time_to_string(job.time, True)))
                if not have:
                        out.write('<h1>No Jobs Found</h1>')
                out.write('</body></html>')
                return out.getvalue()

#单个任务界面（显示单个job_id，该任务下各个task的id和最后更新时间）
class job_view(object):
        def GET(self, job_id):
                out = StringIO.StringIO()
                out.write('<html><head><title>Job %s</title></head><body>/n' % job_id)
                out.write('<h1>JobID: %s</h1>/n' % job_id)
                job = all.get(job_id)
                if not job:
                        out.write('Not Found!')
                else:
                        out.write('<h2>Time: %s</h2>' % time_to_string(job.time, True))
                        out.write('<h2>List of task attempts:</h2>')
                        have = False
                        for attempt, obj in job.attempts.iteritems():
                                have = True
                                out.write('<li><a href="/%s" mce_href="%s">%s</a> Last Update: %s on %s</li>' % (attempt, attempt, time_to_string(obj.time, True), obj.host))
                        if not have:
                                out.write('<h1>No Jobs Found</h1>/n')
                out.write('</body></html>/n')
                return out.getvalue()

def output_seq(name, seq, out, t=False):
        out.write('<tr>')
        out.write('<td>%s</td>/n' % name)
        for v in seq:
                out.write('    <td>%s</td>/n' % (time_to_string(v) if t else str(v)))
        out.write('</tr>')

def output_exeinfo(exe, out):
        out.write('<h2>%s - %s</h2>/n' % (exe.id, exe.exe) )
        out.write('<table>')
        output_seq("Time:", exe.seqs['t'].vs,out,True)
        output_seq("CPU:", exe.seqs['c'].vs,out)
        output_seq("RSS:", exe.seqs['r'].vs,out)
        output_seq("VM:", exe.seqs['v'].vs,out)
        out.write('</table>')

#单个task_attempt界面（显示单个task_attempt界面）
class attempt_view(object):
        def GET(self, attempt_id):
                out = StringIO.StringIO()
                out.write('<html><head><title>Job Attempt %s</title></head><body>/n' % attempt_id)
                jobid = get_jobid_by_attempid(attempt_id)
                job = all.get(jobid)
                if not job:
                        out.write('Not Found!')
                else:
                        attempt = job.attempts.get(attempt_id)
                        if not attempt:
                                out.write('Not Found!')
                        else:
                                out.write('<h1>Attempt run on %s, %s last update: %s</h1>/n' % (attempt.host, attempt_id, time_to_string(attempt.time)))
                                out.write('<h3><a href="/text/%s" mce_href="text/%s">Text Detail</a></h3>/n' % attempt_id)
                                out.write('<image src="/fig/%s.png" mce_src="fig/%s.png" />/n' % attempt_id)
                out.write('</body></html>/n')
                return out.getvalue()


# 单个task_attempt文本界面（显示单个task_attempt时间，CPU，内存信息）
class attempt_text_view(object):
        def GET(self, attempt_id):
                out = StringIO.StringIO()
                out.write('<html><head><title>Job Attempt %s</title></head><body>/n' % attempt_id)
                jobid = get_jobid_by_attempid(attempt_id)
                job = all.get(jobid)
                if not job:
                        out.write('Not Found!')
                else:
                        attempt = job.attempts.get(attempt_id)
                        if not attempt:
                                out.write('Not Found!')
                        else:
                                out.write('<h1>%s last update: %s</h1>/n' % (attempt_id, time_to_string(attempt.time)))
                                for exe in attempt.exes.itervalues():
                                        output_exeinfo(exe, out)
                out.write('</body></html>/n')
                return out.getvalue()

# 单个task_attempt图片界面（显示单个task_attempt时间，CPU，内存信息）
class attempt_fig(object):
        def GET(self, attempt_id):
                jobid = get_jobid_by_attempid(attempt_id)
                job = all.get(jobid)
                if not job:
                        return web.notfound
                attempt = job.attempts.get(attempt_id)
                if not attempt:
                        return web.notfound
                exes = attempt.exes
                fig = plt.figure(figsize=(18,12))
                #内存图
                ax = fig.add_subplot(211)
                for exe in exes.itervalues():
                        pn = "%s(%s)" % (exe.exe, exe.id)
                        ax.plot(exe.seqs['t'].vs, [x/(1024*1024) for x in exe.seqs['r'].vs], label=pn+' RSS')
                        #ax.plot(exe.seqs['t'].vs, exe.seqs['v'].vs, label=pn+' VM')
                plt.ylim(0, 1024) #设置y轴最大最小值
                ax.legend()       #添加图例
                ax.grid(True)     #添加网格
                #CPU图
                ax2 = fig.add_subplot(212)
                for exe in exes.itervalues():
                        pn = "%s(%s)" % (exe.exe, exe.id)
                        ax2.plot(exe.seqs['t'].vs, exe.seqs['c'].vs, label=pn+' CPU')
                plt.ylim(-5, 150)
                ax2.legend()
                ax2.grid(True)
                web.header("Content-Type", "image/png")
                buff = StringIO.StringIO()
                fig.savefig(buff, format='png')
                return buff.getvalue()

class submit_service(object):
        def POST(self):
                c = web.input().get('content')
                records = c.split('/n')
                for r in records:
                        if len(r) < 4:
                                continue
                        add_record(json.loads(r), all)

class save_service(object):
        def GET(self):
                global all
                c = web.input().get('pass')
                if c == 'DEC':
                        fout = open('temp.data', 'w')
                        pickle.dump(all, fout)
                        fout.close()
                        return "SAVE OK"
                else:
                        return web.notfound
        def POST(self):
                self.GET()

class load_service(object):
        def GET(self):
                global all
                c = web.input().get('pass')
                if c == 'DEC':
                        fin = open('temp.data', 'r')
                        all = pickle.load(fin)
                        fin.close()
                        return "LOAD OK"
                else:
                        return web.notfound

class clean_service(object):
        def GET(self):
                global all
                c = web.input().get('pass')
                if c == 'DEC':
                        all = {}
                        fout = open('temp.data', 'w')
                        pickle.dump(all, fout)
                        fout.close()
                        return "SAVE OK"
                else:
                        return web.notfound
if __name__ == "__main__":
        app.run()