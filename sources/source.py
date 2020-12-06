import os
import time


# Abstract
class BackupSource:
    def __init__(self, config, type, suffix):
        self.id = config['id']
        self.type = type
        self.suffix = suffix
        self.tmpdir = "/var/tmp"
        if 'name' in config:
            self.name = config['name']
        if 'tmpdir' in config:
            self.tmpdir = config['tmpdir']

    def dump(self, stats):
        d_starttime = time.time()
        filenames = self.dump()
        d_endtime = time.time()
        stats.dumptime_dump = d_endtime - d_starttime
        if isinstance(filenames, str):
            filenames = [filenames, ]
        files = []

        e_starttime = time.time()
        for filename in filenames:
            files.append(filename)
        e_endtime = time.time()
        return files
