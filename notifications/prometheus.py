import os, os.path
import json
import logging
import base64

from prometheus_client import CollectorRegistry, Gauge, Summary, push_to_gateway
from prometheus_client.exposition import basic_auth_handler

from backups.exceptions import BackupException
from notifications import backupnotification
from notifications.notification import BackupNotification

@backupnotification('prometheus')
class Prometheus(BackupNotification):
    def __init__(self, config):
        BackupNotification.__init__(self, config, 'prometheus')
        self.url = config['url']
        self.username = None
        self.password = None
        if 'credentials' in config:
            self.username = config['credentials']['username']
            self.password = config['credentials']['password']
        self.notify_on_success = True
        self.notify_on_failure = False

    def notify_success(self, source, hostname, filename, stats):
        registry = CollectorRegistry()

        s = Summary('backup_size', 'Size of backup file in bytes', registry=registry)
        s.observe(stats.size)
        s = Summary('backup_dumptime', 'Time taken to dump  in seconds', registry=registry)
        s.observe(stats.dumptime)
        s = Summary('backup_uploadtime', 'Time taken to upload backup in seconds', registry=registry)
        s.observe(stats.uploadtime)
        g = Gauge('backup_timestamp', 'Time backup completed as seconds-since-the-epoch', registry=registry)
        g.set_to_current_time()

        def auth_handler(url, method, timeout, headers, data):
            return basic_auth_handler(url, method, timeout, headers, data, self.username, self.password)

        try:
            push_to_gateway(self.url, job=source.id, registry=registry, handler=auth_handler)
            logging.info("Pushed metrics for job '%s' to gateway (%s)" % (source.id, self.url))
        except Exception as e:
            logging.error("Unable to push metrics for job '%s' to gateway (%s): %s" % (source.id, self.url, str(e)))
