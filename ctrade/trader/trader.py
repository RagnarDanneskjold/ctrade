from ctrade import *
from datetime import datetime
from model import *
from sklearn.ensemble import RandomForestRegressor
import logging
from apscheduler.schedulers.background import BlockingScheduler

import warnings
warnings.filterwarnings("ignore")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class Trading(object):
 
	def __init__(self, pair, indicators):

		self.pair = pair
		self.indicators = indicators
		self.model = None
		self.polo = Poloniex()
		self.signal = None
		self.status = Status()

	def pull_data(self, pair, days, timeframe):

		df = self.polo.chart(pair, days, timeframe).df
		df[pair] = df['close']

		return df

	def train(self, est, days, timeframe):

		logging.info('Pulling the data')
		df = self.pull_data(self.pair, days, timeframe)
		
		logging.info('Training the model')
		m = Model(indicators, self.pair)
		m.set_indicators()
		X = m.get_data(df).dropna()
		Y = m.get_target(df[self.pair]).dropna()
		X, Y = clean_dataset(X, Y)
		self.model  = StackModels(est)
		self.model.fit(X, Y)
		predictions = self.model.stack_predictions()
		self.signal = Signals()
		signals = self.signal.fit(predictions)
		logging.info('Model trained')

	def run(self):

		df = self.pull_data(self.pair, 15, '15m')
		m = Model(indicators, self.pair)
		m.set_indicators()
		X = m.get_data(df).dropna()
		last_prediction = self.model.predict(X)
		last_signal = self.signal.predict(last_prediction)
		last_signal = last_signal.join(df[self.pair], how='inner')
		value = last_signal['signal'].iloc[-1]
		price = last_signal[self.pair].iloc[-1]
		timestamp = last_signal.index[-1].strftime("%Y-%m-%d %H:%M")
		self.status.update(value, price, timestamp)
		print(self.status)


class Status(object):

	def __init__(self):

		self._status = 'Start'
		self._time = None
		self._price = None
		self._time = None
		self.transactions = []
		self.transaction_price = []


	def __repr__(self):
		return '{} - {} - {}'.format(self.time,
									 self.status,
									 self.price)

	@property
	def status(self):
		return self._status

	@status.setter
	def status(self, value):
		self._status = value

	@property
	def time(self):
		return self._time

	@time.setter
	def time(self, value):
		self._time = value

	@property
	def price(self):
		return self._price

	@price.setter
	def price(self, value):
		self._price = value

	def update(self, value, price, timestamp):

		if ((self.status=='Start' or 'Close' in self.status) and value==1):
			self.status = 'Long'
			self.transactions.append(['Long', timestamp])
			self.transaction_price.append(['Long', price])

		if (self.status=='Long' and value==-1):
			self.status = 'Close Long'
			self.transactions[-1] += [timestamp]
			self.transactions[-1] += [price]

		if ((self.status=='Start' or 'Close' in self.status) and value==-1):
			self.status = 'Short'
			self.transactions.append(['Short', timestamp])
			self.transaction_price.append(['Short', price])

		if (self.status=='Short' and value==1):
			self.status = 'Close Short'
			self.transactions[-1] += [timestamp]
			self.transactions[-1] += [price]

		self.time = timestamp
		self.price = price


if __name__=='__main__':

	indicators = {
    'macd': ('macd', {'slow_window': 50, 'fast_window': 15}),
    'rsi': ('rsi', {'window': 15}),
    'fstoc': ('fstoc', {'k_smooth': 8, 'd_smooth': 3}),
    'atr': ('atr', None),
    'bbands': ('bbands', {'mode':'spread'}),
    'pivot_daily': ('pivot', {'mode': 'day'}),
    'pivot_weekly': ('pivot', {'mode': 'week'}),
    'consecutive_periods': ('consecutive_periods', {'add_periods': ['1h', '4h']}),
	}
	logging.info('Start trading')
	est = RandomForestRegressor()
	trader = Trading('BTC_LTC', indicators)
	trader.train(est, 60, '15m')

	scheduler = BlockingScheduler()
	scheduler.add_job(scheduler.start, 
					  'interval', minutes=15,
					  start_date='2017-06-13 22:55:00')
	scheduler.start()

