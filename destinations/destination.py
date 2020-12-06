import datetime

# Abstract
class BackupDestination:
    def __init__(self, config):
        self.id = config['id']
        self.runtime = datetime.datetime.now()

