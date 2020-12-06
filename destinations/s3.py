import os, os.path
import subprocess
import logging

import boto3

import dateutil.parser

from exceptions import BackupException
from destinations import backupdestination
from destinations.destination import BackupDestination

@backupdestination('s3')
class S3(BackupDestination):
    def __init__(self, config):
        BackupDestination.__init__(self, config)
        self.bucket = config['bucket']
        self.region = config['region']
        self.endpoint_url = None
        if 'endpoint_url' in config:
            self.endpoint_url = config['endpoint_url']
        self.aws_key = None
        self.aws_secret = None
        if 'credentials' in config:
            self.aws_key = config['credentials']['aws_access_key_id']
            self.aws_secret = config['credentials']['aws_secret_access_key']

    def send(self, id, name, filename):
        s3location = "s3://%s/%s/%s/%s" % (
            self.bucket,
            id,
            self.runtime.strftime("%Y%m%d%H%M%S"),
            os.path.basename(filename))
        logging.info("Uploading '%s' backup for '%s' to S3 (%s)..." % (name, self.id, s3location))

        uploadargs = ['aws', 's3', 'cp', '--only-show-errors', filename, s3location]
        uploadenv = os.environ.copy()
        if self.aws_key is not None:
            uploadenv['AWS_ACCESS_KEY_ID'] = self.aws_key
            uploadenv['AWS_SECRET_ACCESS_KEY'] = self.aws_secret
            uploadenv['AWS_DEFAULT_REGION'] = self.region
        if self.endpoint_url is not None:
            uploadargs.insert(2, "--endpoint-url")
            uploadargs.insert(3, self.endpoint_url)
        uploadproc = subprocess.Popen(uploadargs, stderr=subprocess.PIPE, env=uploadenv)
        uploadproc.wait()
        exitcode = uploadproc.returncode
        errmsg = uploadproc.stderr.read()
        if exitcode != 0:
            raise BackupException("Error while uploading (%s): %s" % (self.id, errmsg))

        return s3location

    def _boto_kwargs(self):
        kwargs = dict()
        if self.aws_key is not None:
            kwargs['aws_access_key_id'] = self.aws_key
            kwargs['aws_secret_access_key'] = self.aws_secret
        return kwargs

