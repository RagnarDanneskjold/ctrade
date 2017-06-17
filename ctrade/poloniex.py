from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

from .utils import *
from .exceptions import *
from .manager import *

import urllib2, urllib
import time
import json
import hmac
import hashlib
import logging
import pandas as pd

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

__all__ = ['Poloniex']


def createTimeStamp(datestr, format="%Y-%m-%d %H:%M:%S"):
    return time.mktime(time.strptime(datestr, format))


class Poloniex(object):

    def __init__(self):

        self.credentials = Credentials('poloniex')
        self.credentials.load()
        self.currency_pairs = CURRENCY_PAIRS
        self._periods = PERIODS2SEC

    def __getattr__(self, item):
        if hasattr(self.credentials, item):
            return getattr(self.credentials, item)

    def __getitem__(self, item):
        if item in self.currency_pairs:
            return self.ticker()[item]
        else:
            raise CurrencyPairException("'{}' currency pair is not available".format(item))

    def _is_valid_pair(self, pair):
        if pair in self.currency_pairs:
            return pair
        else:
            raise CurrencyPairException("'{}' currency pair is not available".format(pair))

    def _is_valid_period(self, period):
        if period in self.periods:
            return self._periods[period]
        else:
            raise PeriodsException("'{}' period is not available".format(period))

    @property
    def currencies(self):
        return list(set(reduce( lambda x,y: x+y,
                                map(lambda x: x.split('_'),
                                    self.currency_pairs)
                                )
                        )
                    )

    @property
    def periods(self):
        return self._periods.keys()

    def ticker(self):
        return self.pub_api_query({'command': 'returnTicker'})

    def volume(self):
        return self.pub_api_query({'command': 'return24Volume'})

    def orderbook(self, pair):
        if pair != 'all':
            pair = self._is_valid_pair(pair)
        return self.pub_api_query({'command': 'returnOrderBook',
                                   'currencyPair': pair})

    def chart(self, pair, days_back=0, period='5m'):
        pair = self._is_valid_pair(pair)
        period = self._is_valid_period(period)
        start, end = get_start_end(days_back)
        chart =  self.trading_api_query({'command': 'returnChartData',
                                         'currencyPair': pair,
                                         'period': period,
                                         'start': start,
                                         'end': end})

        return Chart(pair, chart, start, end, period)

    def balance(self):
        return self.trading_api_query({'command': 'returnBalances'})

    def complate_balance(self):
        return self.trading_api_query({'command': 'returnCompleteBalances'})

    def trading_history(self, pair, days_back=0):
        if pair != 'all':
            pair = self._is_valid_pair(pair)
        start, end = get_start_end(days_back)
        return self.trading_api_query({'command': 'returnTradeHistory',
                                       'currencyPair': pair,
                                       'start': start,
                                       'end': end})

    def open_orders(self, pair):
        if pair != 'all':
            pair = self._is_valid_pair(pair)
        return self.trading_api_query({'command': 'returnOpenOrders',
                                      'currencyPair': pair})

    def buy(self, pair, rate, amount):
        return self.trading_api_query({'command': 'buy',
                                       'currencyPair': self._is_valid_pair(pair),
                                       'rate': rate,
                                       'amount': amount})

    def sell(self, pair, rate, amount):
        return self.trading_api_query({'command': 'sell',
                                       'currencyPair': self._is_valid_pair(pair),
                                       'rate': rate,
                                       'amount': amount})

    def cancel(self, pair, order_number):
        return self.trading_api_query({'command': 'cancelOrder',
                                       'currencyPair': self._is_valid_pair(pair),
                                       'orderNumber': order_number})

    def withdraw(self, currency, amount, address):
        return self.trading_api_query({'command': 'cancelOrder',
                                       'currency': currency,
                                       'amount': amount,
                                       'address': address})

    def post_process(self, before):
        after = before

        if ('return' in after):
            if (isinstance(after['return'], list)):
                for x in xrange(0, len(after['return'])):
                    if (isinstance(after['return'][x], dict)):
                        if ('datetime' in after['return'][x] and 'timestamp' not in after['return'][x]):
                            after['return'][x]['timestamp'] = float(createTimeStamp(after['return'][x]['datetime']))

        return after


    def pub_api_query(self, commands):

        post_data = self.pub_api + urllib.urlencode(commands)
        returned = urllib2.urlopen(urllib2.Request(post_data))

        return json.loads(returned.read())


    def trading_api_query(self, commands):

        commands['nonce'] = int(time.time() * 1000)
        post_data = urllib.urlencode(commands)

        sign = hmac.new(self.secret, post_data, hashlib.sha512).hexdigest()
        headers = {'Sign': sign,
                   'Key': self.apikey}

        ret = urllib2.urlopen(urllib2.Request(self.trading_api,
                                              post_data,
                                              headers))
        jsonRet = json.loads(ret.read())
        return self.post_process(jsonRet)


class Chart(object):

    def __init__(self, pair, chart, start, end, period):

        self.pair = pair
        self.json = chart
        self._start = start
        self._end = end
        self._period = period

    def __repr__(self):
        return '{} - {} - {} - {}'.format(self.pair,
                                          self.end.strftime('%d/%m %H:%m'),
                                          self.start.strftime('%d/%m %H:%m'),
                                          self.period)

    @property
    def data(self):
        return 'areo'

    @property
    def start(self):
        return datetime.fromtimestamp(self._start)

    @property
    def end(self):
        return datetime.fromtimestamp(self._end)

    @property
    def period(self):
        return {v: k for k,v in PERIODS2SEC.items()}[self._period]

    @property
    def df(self):

        return self._transform()

    def _transform(self):

        series = self.json['candleStick']
        times = perdelta(self.start,
                         self.end,
                         timedelta(**delta_inputs(self.period)))

        times = [i for i in times]
        if len(times) > len(series):
            times = times[:-1]
        elif len(times) < len(series):
            series = series[:-1]
        return pd.DataFrame(series, index=times)