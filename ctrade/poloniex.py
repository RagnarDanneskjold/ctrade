from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

from .utils import *
from .exceptions import *

from ConfigParser import ConfigParser, RawConfigParser
import os
import urllib2, urllib
import time
import json
import logging as LOG

__all__ = ['Credentials',  'Poloniex']


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

def createTimeStamp(datestr, format="%Y-%m-%d %H:%M:%S"):
    return time.mktime(time.strptime(datestr, format))


class Poloniex(object):

    def __init__(self):

        self.credentials = Credentials('poloniex')
        self.credentials.load()

    def __getattr__(self, item):
        if hasattr(self.credentials, item):
            return getattr(self.credentials, item)

    def _is_valid_pair(self):
        if pair in CURRENCY_PAIRS:
            return pair
        else:
            raise CurrencyPairException()

    @property
    def ticker(self):
        return self.pub_api_query({'command': 'returnTicker'})

    @property
    def volume(self):
        return self.pub_api_query({'command': 'return24Volume'})

    @property
    def balances(self):
        return self.pub_api_query({'command': 'returnBalances'})

    @property
    def trade_history(self):
        return self.pub_api_query({'command': 'returnTradeHistory',
                                   'currencyPair': self._is_valid_pair(pair)})

    @property
    def orderbook(self, pair):
        return self.pub_api_query({'command': 'returnOrderBook',
                                   'currencyPair': self._is_valid_pair(pair)})

    @property
    def open_orders(self, pair):
        return self.pub_api_query({'command': 'returnOrderBook',
                                   'currencyPair': self._is_valid_pair(pair)})

    @property
    def buy(self, pair, rate, amount):
        return self.trading_api_query({'command': 'buy',
                                       'currencyPair': self._is_valid_pair(pair),
                                       'rate': rate,
                                       'amount': amount})

    @property
    def sell(self, pair, rate, amount):
        return self.trading_api_query({'command': 'sell',
                                       'currencyPair': self._is_valid_pair(pair),
                                       'rate': rate,
                                       'amount': amount})

    @property
    def cancel(self, pair, order_number):
        return self.trading_api_query({'command': 'cancelOrder',
                                       'currencyPair': self._is_valid_pair(pair),
                                       'orderNumber': order_number})

    @property
    def withdraw(self, currency, amount, address):
        return self.trading_api_query({'command': 'cancelOrder',
                                       'currency': currency,
                                       'amount': amount,
                                       'address': address})

    def post_process(self, before):
        after = before

        # Add timestamps if there isnt one but is a datetime
        if ('return' in after):
            if (isinstance(after['return'], list)):
                for x in xrange(0, len(after['return'])):
                    if (isinstance(after['return'][x], dict)):
                        if ('datetime' in after['return'][x] and 'timestamp' not in after['return'][x]):
                            after['return'][x]['timestamp'] = float(createTimeStamp(after['return'][x]['datetime']))

        return after


    def pub_api_query(self, commands):

        post_data = self.pub_api + '?' + urllib.urlencode(commands)
        returned = urllib2.urlopen(urllib2.Request(post_data))

        return json.loads(returned.read())


    def trading_api_query(self, commands):

            post_data = urllib.urlencode(commands)

            sign = hmac.new(self.secret, post_data, hashlib.sha512).hexdigest()
            headers = {
                'Sign': sign,
                'Key': self.apikey
            }

            ret = urllib2.urlopen(urllib2.Request(self.trading_api,
                                                  post_data,
                                                  headers))
            jsonRet = json.loads(ret.read())
            return self.post_process(jsonRet)
