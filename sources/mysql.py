import os, os.path
import subprocess
import logging

from sources import backupsource
from sources.source import BackupSource
from backups.exceptions import BackupException

@backupsource('mysql')
class MySQL(BackupSource):
    def __init__(self, config, type="MySQL"):
        BackupSource.__init__(self, config, type)
        self.__common_init__(config)

    def __common_init__(self, config):
        self.dbhost = config['dbhost']
        self.dbuser = config['dbuser']
        self.dbpass = config['dbpass']
        self.dbname = config['dbname']

    def dump(self):
        # Create temporary credentials file
        if 'defaults' in dir(self):
            credsfilename = self.defaults
        elif self.dbuser is not None:
            credsfilename = '%s/%s.my.cnf' % (self.tmpdir, self.id)
            credsfile = open(credsfilename, 'w')
            credsfile.write(
                "[client]\n" \
                "host=%s\n" \
                "user=%s\n" \
                "password=%s\n\n" % \
                (self.dbhost, self.dbuser, self.dbpass)
            )
            credsfile.flush()
            credsfile.close()
            os.chmod(credsfilename, 0400)

        # Perform dump and remove creds file
        try:
            dumpfilename = '%s/%s.sql' % (self.tmpdir, self.id)
            logging.info("Backing up '%s' (%s)..." % (self.name, self.type))
            dumpfile = open(dumpfilename, 'wb')
            dumpargs = ['mysqldump', ('--defaults-file=%s' % credsfilename), ('--host=%s' % self.dbhost), '-R']
            if not all_databases:
                dumpargs.append('--databases')
                for dbname in self.dbname.split():
                    dumpargs.append(dbname)
            dumpproc1 = subprocess.Popen(dumpargs, stdout=dumpfile, stderr=subprocess.PIPE)
            if dumpproc1.stdin:
                dumpproc1.stdin.close()
            dumpproc1.wait()
            exitcode = dumpproc1.returncode
            errmsg = dumpproc1.stderr.read()
            if exitcode != 0:
                raise BackupException("Error while dumping: %s" % errmsg)
            dumpfile.close()
        finally:
            os.unlink(credsfilename)

        return [dumpfilename, ]
