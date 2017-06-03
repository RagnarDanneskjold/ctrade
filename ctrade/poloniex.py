from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

from ConfigParser import ConfigParser, RawConfigParser
import os
import urllib2
import datetime, time
from .utils import *
from .exceptions import *
import logging as LOG


def createTimeStamp(datestr, format="%Y-%m-%d %H:%M:%S"):
    return time.mktime(time.strptime(datestr, format))


__all__ = ['Credentials']


AUTH = {
    'poloniex' :
        {'api': [
            'APIKey',
            'Secret',
            'pub_API',
            'trading_API'
        ]},
}

DEFAULT_PROFILE = {
    'poloniex': 'api',
}

class Credentials(object):

    def __init__(self, service):

        self._service = service
        self._home = os.path.expanduser("~")
        self._credential_dir = os.path.join(self._home, '.{}'.format(service))
        self._config_file = os.path.join(self._credential_dir, 'credentials')
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


class Poloniex(object):

    def __init__(self):

        self.credentials = Credentials('poloniex')
        self.location = None

    def __getattr__(self, item):
        if hasattr(self.credentials, item):
            return getattr(self.credentials, item)

    @property
    def ticker(self):
        return self.pub_api_query({'command': 'returnTicker'})

    @property
    def volume(self):
        return self.pub_api_query({'command': 'return24Volume'})

    @property
    def orderbook(self, pair):
        return self.pub_api_query({'command': 'returnOrderBook',
                                  'currencyPair': pair})

    @property
    def trade_history(self, pair):
        return self.pub_api_query({'command': 'returnTradeHistory'})


    def _is_valid_pair(self):
        if pair in CURRENCY_PAIRS:
            return True
        else:
            raise CurrencyPairException()


    def pub_api_query(self, commands):

        post_data = self.pub_API + urllib.urlencode(commands)
        returned = urllib2.urlopen(urllib2.Request(post_data)

        return json.loads(returned.read())


    def trading_api_query(self, commands):

            post_data = urllib.urlencode(commands)

            sign = hmac.new(self.Secret, post_data, hashlib.sha512).hexdigest()
            headers = {
                'Sign': sign,
                'Key': self.APIKey
            }

            ret = urllib2.urlopen(urllib2.Request(self.trading_API,
                                                  post_data,
                                                  headers))
            jsonRet = json.loads(ret.read())
            return self.post_process(jsonRet)


