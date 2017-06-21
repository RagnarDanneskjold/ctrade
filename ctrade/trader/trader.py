from model import *
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
import logging
import argparse
import time
from ctrade import *
from datetime import datetime

import warnings
warnings.filterwarnings("ignore")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DATA_FORMAT = "%Y-%m-%d %H:%M"

class Trading(object):
 
    def __init__(self, pair, indicators):

        self.pair = pair
        self.indicators = indicators
        self.model = None
        self.polo = Poloniex()
        self.signal = None
        self.m = Model(indicators, pair)
        self.status = Status(pair)
        self.manager = FileManager(pair)
        self.signal = Signals(pair)

    def _pull_data(self, days, timeframe):

        maxi = False
        while not maxi:
            try:
                df = self.polo.chart(self.pair, days, timeframe).df
                maxi = True
            except:
                time.sleep(10)

        df[self.pair] = df['close']

        return df

    def pull_data(self, days, timeframe):

        if self.manager.islast(save_type='prediction_data'):
            last_df = self.manager.get_last(save_type='prediction_data')
            size = last_df.shape[0]
            df = self._pull_data(0, timeframe)
            mask = df.index.isin(last_df.index)
            df = pd.concat([last_df, df[~mask]]).iloc[-size:]
        else:
            df = self._pull_data(days, timeframe)

        self.manager.save(df, save_type='prediction_data')
        self.manager.clear(save_type='prediction_data')
        df[self.pair] = df['close']

        return df

    def train(self, est, days, timeframe):

        logging.info('Pulling the data')
        df = self._pull_data(days, timeframe)

        logging.info('Training the model')
        self.m = Model(self.indicators, self.pair)
        self.model  = StackModels(est)

        self.m.set_indicators()
        X = self.m.get_data(df).dropna()
        Y = self.m.get_target(df[self.pair]).dropna()
        X, Y = clean_dataset(X, Y)
        self.model.fit(X, Y)
        predictions = self.model.stack_predictions()
        _ = self.signal.fit(predictions)
        logging.info('Model trained')

    def run(self):
        date = datetime.now().strftime(DATA_FORMAT)
        logging.info('{} Doing new predictions'.format(date))

        df = self.pull_data(15, '15m')
        X = self.m.get_data(df).dropna()
        last_prediction = self.model.predict(X)
        save_prediction = last_prediction.iloc[-1]*np.array(self.model.factors)
        self.manager.save(save_prediction,
                          save_type='predictions')
        last_signal = self.signal.predict(last_prediction)
        last_signal = last_signal.join(df[self.pair], how='inner')

        self.status.update(last_signal)


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
    post_message('cryptobot',
    			 'STARTED TRADING {} USING MODEL...'.format(inputs.pair),
    			 username='cryptobot',
    			 icon=':matrix:')

    logging.info('Start trading')
    est = GradientBoostingRegressor(n_estimators=40,
                                    min_samples_leaf=20,
                                    max_depth=3,
                                    subsample=0.3)
    trader = Trading(inputs.pair, indicators)
    trader.train(est, 60, '15m')
    trader.run()

    t = time.time()
    while True:
        if time.time()-t>900:
            t = time.time()
            trader.run()

        time.sleep(900)

