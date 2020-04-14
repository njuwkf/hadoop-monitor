#!usr/bin/python
# -*- coding: utf-8 -*-
import sys
import traceback
import time
import socket
import threading
import json
import psutil
import httplib
import urllib
hostname = socket.gethostname()

#获取attempt_id
def get_attempt_id(pid):
    current = pid
    while (True):
        if current <= 1000:
            return None
        p = psutil.Process(current)
        cmd = " ".join(p.cmdline())
        pos = cmd.find(" attempt_")
        if pos > 0:
            end = cmd.find(" ", pos + 1)
            if end == -1:
                return cmd[pos + 1]
            return cmd[pos + 1:end]
        current = p.ppid()

#获取进程信息
def get_event(pid, attempt_id, t):
    p = psutil.Process(pid)
    meminfo = p.memory_info()
    timeinfo = p.cpu_times()
    info = {"attempt": attempt_id[0],
            "pid": pid,
            "cmd": p.cmdline(),
            "start": p.create_time(),
            "current": t,
            "tuser": timeinfo[0],
            "tsystem": timeinfo[1],
            "rss": 1.0*meminfo[0],
            "vms": 1.0*meminfo[1],
            "cpu": p.cpu_percent(interval=1),
            "threads": p.num_threads(),
            "host": hostname}
    ret = json.dumps(info)
    return ret+"\n"


usefull_pids = {}
rubbish_pids = {}
event_buffer = []
event_buffer_lock = threading.Lock()

#进程信息更新
def check_processes():
    global event_buffer
    # check for new process
    pids = psutil.pids()
    for pid in pids:
        if usefull_pids.has_key(pid):
            continue
        if rubbish_pids.has_key(pid):
            continue
        attempt_id = get_attempt_id(pid)
        if attempt_id:
            sys.stderr.write("Get new process [%d] for hadoop task attempt [%s]\n" % (pid, attempt_id))
            usefull_pids[pid] = (attempt_id, psutil.Process(pid))
        else:
            rubbish_pids[pid] = pid
    for pid in usefull_pids.keys():
        if pid not in pids:
            del usefull_pids[pid]
    for pid in rubbish_pids.keys():
        if pid not in pids:
            del rubbish_pids[pid]
    # update old process
    t = int(time.time())
    for pid, attempt_id in usefull_pids.iteritems():
        try:
            event_str = get_event(pid, attempt_id, t)
            with event_buffer_lock:
                event_buffer.append(event_str)
        except:
            sys.stderr.write("Get event info error, pid=%d, attempt_id=%s" % (pid, attempt_id[0]))
            sys.stderr.flush()

#循环读取信息
def loop():
    global event_buffer
    while (True):
        try:
            check_processes()
        except:
            traceback.print_exc()
        time.sleep(1.5)
        if len(event_buffer) > 1024 * 32:
            with event_buffer_lock:
                event_buffer = event_buffer[1024 * 4:]

#读取信息线程开关
read_thread_run = True

#本地调试
def local_read_thread():
    global event_buffer
    global read_thread_run
    while read_thread_run:
        if len(event_buffer) > 0:
            with event_buffer_lock:
                ready = event_buffer
                event_buffer = []
            for e in ready:
                print e
        time.sleep(1.5)


#网络请求
def http_send_thread(post_url):
    global event_buffer
    global read_thread_run
    if post_url.startswith("http://"):
        post_url = post_url[7:]
    try:
        host, path = post_url.split('/', 1)
        path = '/' + path
    except:
        host = post_url
        path = '/'
    while read_thread_run:
        while len(event_buffer) <= 0 and read_thread_run:
            time.sleep(1.5)
        if not read_thread_run:
            break
        try:
            length = len(event_buffer)
            conn = httplib.HTTPConnection(host)
            params = urllib.urlencode({"content": "".join(event_buffer[:length])})
            conn.request(method="POST", url=path, body=params)
            rep = conn.getresponse()
            print event_buffer
            print rep.status
            if rep.status == httplib.OK:
                with event_buffer_lock:
                    # print "[%d/%d] send" % (length, len(event_buffer))
                    event_buffer = event_buffer[length:]
            else:
                print "HTTP post error: %s" % rep.status
                time.sleep(10)
        except:
            traceback.print_exc()
            time.sleep(10)


if __name__ == "__main__":
    read_thread_run = True
    t = threading.Thread(target=http_send_thread,args=["127.0.0.1:8080/submit"])
    t.start()
    try:
        loop()
    finally:
        read_thread_run = False
    t.join()
