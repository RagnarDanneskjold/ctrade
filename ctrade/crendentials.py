from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

from ConfigParser import ConfigParser, RawConfigParser
import os
import logging

logger = logging.getLogger(__name__)


__all__ = ['Credentials']


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
            'Secret',
            'token',
            'webhook_url'
        ]}
}

DEFAULT_PROFILE = {
    'poloniex': 'api',
}

class Credentials(object):

    def __init__(self, service):

        self._service = service
        self._home = os.path.expanduser("~")
        self._credential_dir = os.path.join(self._home, '.credentials')
        self._config_file = os.path.join(self._credential_dir, '{}'.format(service))
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
        LOG.info("Creating config file in {}".format(self._credential_dir))
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
            LOG.warning("A config files was found. Press 0 to proceed.")

            if raw_input() != '0':
                LOG.warning("Aborting configuration.")
                return None

        if params is None:
            params = {}
            for k in AUTH[self._service][DEFAULT_PROFILE[self._service]]:
                params[k] = raw_input("Enter {}: "\
                                      .format(' '.join(k.split('_'))))

        self.create_config_file(params)