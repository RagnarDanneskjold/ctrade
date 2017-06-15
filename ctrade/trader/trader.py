from ctrade import *
from datetime import datetime
from model import *
from sklearn.ensemble import RandomForestRegressor
import logging
from apscheduler.schedulers.background import BackgroundScheduler
import argparse
import time

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
		self.m = Model(indicators, pair)
		self.status = Status(pair)

	def pull_data(self, pair, days, timeframe):

		df = self.polo.chart(pair, days, timeframe).df
		df[pair] = df['close']

		return df

	def train(self, est, days, timeframe):

		logging.info('Pulling the data')
		df = self.pull_data(self.pair, days, timeframe)
		
		logging.info('Training the model')
		self.m = Model(indicators, self.pair)
		self.m.set_indicators()
		X = self.m.get_data(df).dropna()
		Y = self.m.get_target(df[self.pair]).dropna()
		X, Y = clean_dataset(X, Y)
		self.model  = StackModels(est)
		self.model.fit(X, Y)
		predictions = self.model.stack_predictions()
		self.signal = Signals()
		signals = self.signal.fit(predictions)
		logging.info('Model trained')

	def run(self):

		df = self.pull_data(self.pair, 15, '15m')
		X = self.m.get_data(df).dropna()
		last_prediction = self.model.predict(X)
		last_signal = self.signal.predict(last_prediction)
		last_signal = last_signal.join(df[self.pair], how='inner')
		value = last_signal['signal'].iloc[-1]
		price = last_signal[self.pair].iloc[-1]
		timestamp = last_signal.index[-1].strftime("%Y-%m-%d %H:%M")
		self.status.update(value, price, timestamp)

class Status(object):

	def __init__(self, pair):

		self.pair = pair
		self._status = 'Started'
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

	def notify(self):
		if len(self.transactions[-1])==2:
			msg = "{} - Entered {} position for {} at {}".format(datetime.now(), 
																 self.status, 
																 self.pair,
																 self.price[-1][1])
		else:
			if 'Short' in self.status:
				gain =  (self.price[-1][1] - self.price[-1][2])/self.price[-1][1] 
			elif 'Long' in self.status:
				gain =  (self.price[-1][2] - self.price[-1][1])/self.price[-1][1] 

			date = datetime.now().strftime("%Y-%m-%d %H:%M")
			msg = "{} - Closed {} position for {} at {} - ".format(date, 
																   self.status, 
																   self.pair,
																   self.price[-1][1])
		with open('~/trader-{}.log'.format(self.pair), 'a') as f:
			f.write(msg)

		logging.info(msg)

		# post_message('cryptobot', msg, username='cryptobot', icon=':matrix:')

	def update(self, value, price, timestamp):

		if ((self.status=='Started' or 'Close' in self.status) and value==1):
			self.status = 'Long'
			self.transactions.append(['Long', timestamp])
			self.transaction_price.append(['Long', price])
			event = True

		elif (self.status=='Long' and value==-1):
			self.status = 'Close Long'
			self.transactions[-1] += [timestamp]
			self.transactions[-1] += [price]
			event = True

		elif ((self.status=='Started' or 'Close' in self.status) and value==-1):
			self.status = 'Short'
			self.transactions.append(['Short', timestamp])
			self.transaction_price.append(['Short', price])
			event = True

		elif (self.status=='Short' and value==1):
			self.status = 'Close Short'
			self.transactions[-1] += [timestamp]
			self.transactions[-1] += [price]
			event = True

		else:
			event = False

		if event:
			self.notify()

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


	parser = argparse.ArgumentParser(description='Trading script')
	parser.add_argument('-cp','--currency_pair', dest='pair',
		help='Currency pair to use', 
		default='BTC_LTC')

	inputs = parser.parse_args()
	# post_message('cryptobot', 
	# 			 'STARTED TRADING USING MODEL...', 
	# 			 username='cryptobot', 
	# 			 icon=':matrix:')

	logging.info('Start trading')
	est = RandomForestRegressor()
	trader = Trading(inputs.pair, indicators)
	trader.train(est, 60, '15m')
	trader.run()

	t = time.time()
	while True:
		if time.time()-t>60:
			t = time.time()
			trader.run()
		
		time.sleep(60)

