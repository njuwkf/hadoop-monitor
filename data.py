#!usr/bin/python
# -*- coding: utf-8 -*-

#job类
class Job(object):
        def __init__(self, jobid, parent):
                self.id = jobid
                self.attempts = {}
                self.seqs = {}
                self.time = 0
                self.start_time = 0
                self.parent = parent
        def set_start_time(self,t):
                self.start_time = t
        def set_time(self, t):
                self.time = t
        def get(self,id,host=None):
                ret = self.attempts.get(id)
                if ret == None:
                        ret = Attempt(id, host, self)
                        self.attempts[id] = ret
                return ret
        def getseq(self,id):
                ret = self.seqs.get(id)
                if ret == None:
                        ret = JobSeq(id, self)
                        self.seqs[id] = ret
                return ret

#job单个资源记录（CPU，RSS，VMS）
class JobSeq(object):
        def __init__(self, name, parent):
                self.id = name
                self.vs = []
                self.dict = {}
                self.parent = parent


#attempt类
class Attempt(object):
        def __init__(self, attemptid, host, parent):
                self.id = attemptid
                self.exes = {}
                self.time = 0
                self.host = host
                self.parent = parent
        def set_time(self, t):
                self.time = t
                self.parent.set_time(t)
        def get(self,id, exe=None):
                ret = self.exes.get(id)
                if ret == None:
                        ret = Exe(id, exe, self)
                        self.exes[id] = ret
                return ret

#进程类
class Exe(object):
        def __init__(self, pid, exe, parent):
                self.id = pid
                self.exe = exe
                self.seqs = {}
                self.time = 0
                self.parent = parent
        def set_time(self, t):
                self.time = t
                self.parent.set_time(t)
        def get(self,id):
                ret = self.seqs.get(id)
                if ret == None:
                        ret = Seq(id, self)
                        self.seqs[id] = ret
                return ret

#进程单个资源记录（CPU，RSS，VMS）
class Seq(object):
        def __init__(self, name, parent):
                self.id = name
                self.vs = []
                self.dict = {}
                self.time = 0
                self.parent = parent
        def append_time(self, t):
                self.time = t
                self.parent.set_time(t)