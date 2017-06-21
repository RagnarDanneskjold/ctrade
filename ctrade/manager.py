from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

from ConfigParser import ConfigParser, RawConfigParser
import os
import logging
import glob
import pandas as pd
from ctrade import *
from datetime import datetime
import pickle

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

__all__ = ['Credentials', 'FileManager']

DATA_FORMAT = "%Y-%m-%d_%H.%M"

AUTH = {
    'poloniex' :
        {'api': [
            'APIKey',
            'Secret',
            'pub_API',
            'trading_API'
        ]},

    'slack':
        {'crypto-bot': [
            'client_id',
            'client_secret',
            'verification_token',
            'webhook_url'
        ]}
}

DEFAULT_PROFILE = {
    'poloniex': 'api',
    'slack': 'crypto-bot'
}

class Credentials(object):

    def __init__(self, service):

        self._service = service
        self._home = os.path.expanduser("~")
        self._credential_dir = os.path.join(self._home, '.credentials')
        self._config_file = os.path.join(self._credential_dir,
                                         '{}'.format(service))
        self.credentials = {}
        if not os.path.isdir(self._credential_dir):
            os.mkdir(self._credential_dir)

    def __getattr__(self, item):
        if item in self.credentials.keys():
            return self.credentials[item]

    def __str__(self):
        return "\n".join( ["{}: {}".format(k, v) \
                           for k, v in self.credentials.items()] )

    @property
    def name(self):
        return self._service

    def config_exists(self):
        return os.path.isfile(self._config_file)

    def create_config_file(self, params):
        logger.info("Creating config file in {}".format(self._credential_dir))
        config = RawConfigParser()
        config.add_section(DEFAULT_PROFILE[self._service])

        for k, v in params.items():
            config.set(DEFAULT_PROFILE[self._service], k, v)

        with open(self._config_file, 'wb') as file:
            config.write(file)

    def load(self):
        config = ConfigParser()
        config.read(self._config_file)

        for k, v in config.items(DEFAULT_PROFILE[self._service]):
            self.credentials[k] = v

    def configure(self, params=None):
        """Configure or over-write Lotame API credentials
        in ~/.lotame/config
        """
        if self.config_exists():
            logger.warning("A config files was found. Press 0 to proceed.")

            if raw_input() != '0':
                logger.warning("Aborting configuration.")
                return None

        if params is None:
            params = {}
            for k in AUTH[self._service][DEFAULT_PROFILE[self._service]]:
                params[k] = raw_input("Enter {}: "\
                                      .format(' '.join(k.split('_'))))

        self.create_config_file(params)

save_types = ['predictions', 'prediction_data', 'quantiles']

class FileManager(object):

    def __init__(self, pair):

        self._pair = pair
        self._home = os.path.expanduser("~")
        self._data_dir = os.path.join(self._home, 'data')
        self._data = os.path.join(self._data_dir, pair)
        self.check()

    def check(self):

        if not os.path.isdir(self._data_dir):
            os.mkdir(self._data_dir)
        if not os.path.isdir(self._data):
            os.mkdir(self._data)

    def save(self, df, save_type='predictions'):

        date = datetime.now().strftime(DATA_FORMAT)
        filename = self._data + '/{}-{}-{}.pkl'.format(date,
                                                       save_type,
                                                       self._pair)
        try:
            df.to_pickle(filename)
        except:
            pickle.dump(df, open(filename, 'wb'))

    def get_last(self, save_type='predictions'):

        files = self.files(save_type=save_type)
        file = sorted(files)[-1]
        try:
            return pd.read_pickle(file)
        except:
            return pickle.load(open(file, 'r'))

    def files(self, save_type='predictions'):
        files = glob.glob(self._data +
                          '/*{}-{}.pkl'.format(save_type,
                                               self._pair))
        return sorted(files)

    def islast(self, save_type='predictions'):
        files = self.files(save_type=save_type)
        if len(files)>0:
            date = files[-1].split('/')[-1].split('-'+save_type)[0]
            date = datetime.strptime(date, DATA_FORMAT)
            time_from_last = (datetime.now() - date).total_seconds()/60
            if time_from_last<100:
                return len(files)>0
            else:
                return False
        else:
            return False

    def clear(self, save_type=None):

        if save_type is not None:
            files = self.files(save_type=save_type)
            if len(files)>1:
                for file in files[:-1]:
                    os.remove(file)
        else:
            for save_type in save_types:
                files = self.files(save_type=save_type)
                if len(files)>1:
                    for file in files[:-1]:
                        os.remove(file)


