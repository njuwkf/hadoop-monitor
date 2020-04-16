#!usr/bin/python
# -*- coding: utf-8 -*-

import json
import web
import cStringIO as StringIO
import matplotlib.pyplot as plt
from matplotlib.pyplot import MultipleLocator
import cPickle as pickle

from util import get_jobid_by_attempid, time_to_string, add_record

plt.switch_backend('agg')


urls = (
        '/', 'jobs_view',
        '/jobs', 'jobs_view',
        '/job_([_\d]+)', 'job_view',
        '/job_info_([_\d]+)', 'job_info_view',
        '/(attempt_[^\s]+)', 'attempt_view',
        '/text/(attempt_[^\s]+)', 'attempt_text_view',
        '/fig/(attempt_[^\s]+).png', 'attempt_fig',
        '/submit', 'submit_service',
        '/save', 'save_service',
        '/load', 'load_service',
        '/clean', 'clean_service',
        '/text/([^\s]+)', 'job_info_text_view',
        '/fig/([^\s]+).png', 'job_info_fig',
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
                        out.write('<li><a href="/job_%s">job %s</a> Last Update: %s  <a href="/job_info_%s">about job info</a></li>' % (jobid,jobid, time_to_string(job.time, True),jobid))
                if not have:
                        out.write('<h1>No Jobs Found</h1>')
                out.write('</body></html>')
                return out.getvalue()
        def POST(self):
                self.GET()


# 单个任务界面（显示单个job_id，该任务下各个task的id和最后更新时间）
class job_view(object):
        def GET(self, job_id):
                out = StringIO.StringIO()
                out.write('<html><head><title>Job %s</title></head><body>' % job_id)
                out.write('<h1>JobID: %s</h1>' % job_id)
                job = all.get(job_id)
                if not job:
                        out.write('Not Found!')
                else:
                        out.write('<h2>Start Time: %s</h2>' % time_to_string(job.start_time, True))
                        out.write('<h2>List of task attempts:</h2>')
                        have = False
                        for attempt, obj in job.attempts.iteritems():
                                have = True
                                out.write('<li><a href="/%s">%s</a> Last Update: %s on %s</li>' % (attempt,attempt, time_to_string(obj.time, True), obj.host))
                        if not have:
                                out.write('<h1>No Jobs Found</h1>')
                out.write('</body></html>')
                return out.getvalue()
        def POST(self, job_id):
                self.GET(job_id)

#单个task_attempt界面（显示单个task_attempt界面）
class attempt_view(object):
        def GET(self, attempt_id):
                out = StringIO.StringIO()
                out.write('<html><head><title>Job Attempt %s</title></head><body>' % attempt_id)
                jobid = get_jobid_by_attempid(attempt_id)
                job = all.get(jobid)
                if not job:
                        out.write('Not Found!')
                else:
                        attempt = job.attempts.get(attempt_id)
                        if not attempt:
                                out.write('Not Found!')
                        else:
                                out.write('<h1>Attempt run on %s, %s last update: %s</h1>' % (attempt.host, attempt_id, time_to_string(attempt.time)))
                                out.write('<h3><a href="/text/%s" >Text Detail</a></h3>' % (attempt_id))
                                out.write('<image src="/fig/%s.png" />' % (attempt_id))
                out.write('</body></html>\n')
                return out.getvalue()
        def POST(self, attempt_id):
                self.GET(attempt_id)

def output_seq(name, seq, out, t=False,first=False):
        out.write('<tr>')
        out.write('<td>%s</td>\n' % name)
        for v in seq:
                if first:
                        out.write('    <td>%s</td>\n' % (time_to_string(v[0]) if t else str(v[0])))
                else:
                        out.write('    <td>%s</td>\n' % (time_to_string(v[1]) if t else str(v[1])))
        out.write('</tr>')

def output_exeinfo(exe, out):
        out.write('<h2>%s - %s</h2>\n' % (exe.id, exe.exe) )
        out.write('<table>')
        output_seq("Time:", exe.seqs['c'].vs,out,True,True)
        output_seq("CPU:", exe.seqs['c'].vs,out)
        output_seq("RSS(MB):", exe.seqs['r'].vs,out)
        output_seq("VM(MB):", exe.seqs['v'].vs,out)
        out.write('</table>')

# 单个task_attempt文本界面（显示单个task_attempt时间，CPU，内存信息）
class attempt_text_view(object):
        def GET(self, attempt_id):
                out = StringIO.StringIO()
                out.write('<html><head><title>Job Attempt %s</title></head><body>\n' % attempt_id)
                jobid = get_jobid_by_attempid(attempt_id)
                job = all.get(jobid)
                if not job:
                        out.write('Not Found!')
                else:
                        attempt = job.attempts.get(attempt_id)
                        if not attempt:
                                out.write('Not Found!')
                        else:
                                out.write('<h1>%s last update: %s</h1>\n' % (attempt_id, time_to_string(attempt.time)))
                                for exe in attempt.exes.itervalues():
                                        output_exeinfo(exe, out)
                out.write('</body></html>\n')
                return out.getvalue()
        def POST(self, attempt_id):
                self.GET(attempt_id)

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
                fig = plt.figure(figsize=(15,10))
                #内存图
                ax = fig.add_subplot(211)
                for exe in exes.itervalues():
                        pn = "%s(%s)" % (exe.exe, exe.id)
                        ax.plot([time_to_string(x[0]) for x in exe.seqs['r'].vs], [x[1] for x in exe.seqs['r'].vs], 'm.-',label=pn+' RSS',linewidth=1)
                # 设置y轴范围
                plt.ylim(0, 1024)
                #坐标轴朝内
                plt.rcParams['xtick.direction'] = 'in'
                plt.rcParams['ytick.direction'] = 'in'
                #设置坐标轴名称
                plt.xlabel('RSS(MB)')
                plt.ylabel('Time')
                x_major_locator = MultipleLocator(10)
                ax.xaxis.set_major_locator(x_major_locator)
                ax.legend()       #添加图例
                #CPU图
                ax2 = fig.add_subplot(212)
                for exe in exes.itervalues():
                        pn = "%s(%s)" % (exe.exe, exe.id)
                        ax2.plot([time_to_string(x[0]) for x in exe.seqs['c'].vs],[x[1] for x in exe.seqs['c'].vs], 'm.-',label=pn+' CPU',linewidth=1)
                plt.ylim(-5, 150)
                plt.rcParams['xtick.direction'] = 'in'
                plt.rcParams['ytick.direction'] = 'in'
                # 设置坐标轴名称
                plt.xlabel('CPU')
                plt.ylabel('Time')
                x_major_locator = MultipleLocator(10)
                ax2.xaxis.set_major_locator(x_major_locator)
                ax2.legend()
                web.header("Content-Type", "image/png")
                buff = StringIO.StringIO()
                fig.savefig(buff, format='png')
                return buff.getvalue()
        def POST(self, attempt_id):
                self.GET(attempt_id)


#显示单个job界面
class job_info_view(object):
        def GET(self, job_id):
                out = StringIO.StringIO()
                out.write('<html><head><title>Job %s</title></head><body>' % job_id)
                job = all.get(job_id)
                if not job:
                        out.write('Not Found!')
                else:
                        out.write('<h1>Job %s last update: %s</h1>' % (job_id, time_to_string(job.time)))
                        out.write('<h3><a href="/text/%s" >Text Detail</a></h3>' % (job_id))
                        out.write('<image src="/fig/%s.png" />' % (job_id))
                out.write('</body></html>\n')
                return out.getvalue()
        def POST(self, job_id):
                self.GET(job_id)


# 单个job文本界面（显示单个job时间，CPU，内存信息）
class job_info_text_view(object):
        def GET(self, job_id):
                out = StringIO.StringIO()
                out.write('<html><head><title>Job %s</title></head><body>\n' % job_id)
                job = all.get(job_id)
                if not job:
                        out.write('Not Found!')
                else:
                        out.write('<h1>Job %s last update: %s</h1>\n' % (job_id, time_to_string(job.time)))
                        out.write('<table>')
                        output_seq("Time:", job.seqs['c'].vs, out, True, True)
                        output_seq("CPU:", job.seqs['c'].vs, out)
                        output_seq("RSS(MB):", job.seqs['r'].vs, out)
                        output_seq("VM(MB):", job.seqs['v'].vs, out)
                        out.write('</table>')
                out.write('</body></html>\n')
                return out.getvalue()
        def POST(self, job_id):
                self.GET(job_id)

# 单个job图片界面（显示单个job时间，CPU，内存信息）
class job_info_fig(object):
        def GET(self, job_id):
                job = all.get(job_id)
                if not job:
                        return web.notfound
                fig = plt.figure(figsize=(15,10))
                #内存图
                ax = fig.add_subplot(211)
                pn = "%s" % (job_id)
                ax.plot([time_to_string(x[0]) for x in job.seqs['r'].vs], [x[1] for x in job.seqs['r'].vs], 'm.-',label=pn+' RSS',linewidth=1)
                # 设置y轴范围
                plt.ylim(0, 1024)
                #坐标轴朝内
                plt.rcParams['xtick.direction'] = 'in'
                plt.rcParams['ytick.direction'] = 'in'
                #设置坐标轴名称
                plt.xlabel('RSS(MB)')
                plt.ylabel('Time')
                x_major_locator = MultipleLocator(10)
                ax.xaxis.set_major_locator(x_major_locator)
                ax.legend()       #添加图例
                #CPU图
                ax2 = fig.add_subplot(212)
                pn = "%s" % (job_id)
                ax2.plot([time_to_string(x[0]) for x in job.seqs['c'].vs],[x[1] for x in job.seqs['c'].vs], 'm.-',label=pn+' CPU',linewidth=1)
                plt.ylim(-5, 150)
                plt.rcParams['xtick.direction'] = 'in'
                plt.rcParams['ytick.direction'] = 'in'
                # 设置坐标轴名称
                plt.xlabel('CPU')
                plt.ylabel('Time')
                x_major_locator = MultipleLocator(10)
                ax2.xaxis.set_major_locator(x_major_locator)
                ax2.legend()
                web.header("Content-Type", "image/png")
                buff = StringIO.StringIO()
                fig.savefig(buff, format='png')
                return buff.getvalue()
        def POST(self, job_id):
                self.GET(job_id)


class submit_service(object):
        def POST(self):
                global all
                c = web.input().get('content')
                records = c.split('\n')
                for r in records:
                        if len(r) < 4:
                                continue
                        add_record(json.loads(r), all)
        def GET(self):
                self.POST()

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
        def POST(self):
                self.GET()

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
        def POST(self):
                self.GET()

if __name__ == "__main__":
        app.run()
