#!/usr/bin/env python

import os
import os.path
import sys
import datetime
import time
import argparse
import getpass
import logging
import logging.handlers
import json

import stats
import sources
import destinations
import notifications

from backups.exceptions import BackupException

# Default set of modules to import
default_modules = [
    'sources.mysql',
    'destinations.s3',
    'notifications.prometheus',
]

class BackupRunInstance:
    def __init__(self):
        import platform
        self.hostname = platform.node()
        self.source_modules = []
        self.sources = []
        self.destination_modules = []
        self.destinations = []
        self.notification_modules = []
        self.notifications = []
        self.stats = backups.stats.BackupRunStatistics()

    def run(self):
        # Loop through the defined source modules...
        for source in self.sources:
            # Trigger notifications as required
            for notification in self.notifications:
                notification._notify_start(source, self.hostname)

            try:
                # Dump
                starttime = time.time()
                self.stats.starttime = datetime.datetime.now()
                dumpfiles = source.dump(self.stats)
                if not isinstance(dumpfiles, list):
                    dumpfiles = [dumpfiles, ]
                endtime = time.time()
                self.stats.dumptime = endtime - starttime

                # Add up backup file sizes
                totalsize = 0
                for dumpfile in dumpfiles:
                    totalsize = totalsize + os.path.getsize(dumpfile)
                self.stats.size = totalsize

                # Send each dump file to each listed destination
                starttime = time.time()
                self.stats.dumpedfiles = []
                self.stats.retainedfiles = []
                for dumpfile in dumpfiles:
                    for destination in self.destinations:
                        self.stats.dumpedfiles.append(destination.send(source.id, source.name, dumpfile))
                        self.stats.retainedfiles += destination.cleanup(source.id, source.name)
                endtime = time.time()
                self.stats.endtime = datetime.datetime.now()
                self.stats.uploadtime = endtime - starttime

                # Trigger success notifications as required
                for notification in self.notifications:
                    notification._notify_success(source, self.hostname, dumpfile, self.stats)

            except Exception as e:
                import traceback
                traceback.print_exc()
                # Trigger notifications as required
                for notification in self.notifications:
                    notification._notify_failure(source, self.hostname, e)

            finally:
                # Done with the dump file now
                if 'dumpfile' in locals() and os.path.isfile(dumpfile):
                   os.unlink(dumpfile)

        logging.debug("Complete.")

def main():
    try:
        # Read arguments
        parser = argparse.ArgumentParser()
        parser.add_argument('configfile', metavar='configfile', nargs=1,
                   help='name of configuration file to use for this run')
        parser.add_argument('-v', dest='verbose', action='store_true')
        parser.add_argument('-d', dest='debug', action='store_true')
        args = parser.parse_args()
        configfile = args.configfile[0]

        # Enable logging if verbosity needed
        if args.debug:
            logging.basicConfig(level=logging.DEBUG)
        elif args.verbose:
            logging.basicConfig(level=logging.INFO)

        # Read Json
        with open(configfile) as json_conf:
            config = json.load(json_conf)

        # Import modules
        backup_modules = config['modules']
        if backup_modules is None:
            backup_modules = default_modules
        for modulename in backup_modules:
            logging.debug("Importing module '%s'" % modulename)
            try:
                module = __import__(modulename)
            except ImportError as e:
                logging.error("Error importing module: %s" % e.__str__())

        # Handlers for destination
        destinations = []
        for dest_id, dest_class in destinations.handlers.items():
            logging.debug("Dest(%s) - %s" % (dest_id, dest_class))
            for dest_config in config['destinations']:
                if dest_config['type'] == dest_id:
                    destination = dest_class(dest_config)
                    destinations.append(destination)

        # Handlers for notifications
        notifications = []
        for notify_id, notify_class in notifications.handlers.items():
            logging.debug("Notify(%s) - %s" % (notify_id, notify_class))
            for notify_config in config['notifications']:
                if notify_config['type'] == notify_id:
                    notification = notify_class(notify_config)
                    notifications.append(notification)

        # Find a source from where create backup
        sources = []
        for source_id, source_class in sources.handlers.items():
            logging.debug("Source(%s) - %s" % (source_id, source_class))
            for source_config in config['sources']:
                if source_config['type'] == source_id:
                    source = source_class(source_config)
                    sources.append(source)

        if len(sources) < 1:
            raise BackupException("No sources listed in configuration file.")

        instance = BackupRunInstance()
        instance.notifications = notifications
        instance.sources = sources
        instance.destinations = destinations
        instance.run()

    except KeyboardInterrupt :
        sys.exit()

if __name__ == '__main__':
    main()
