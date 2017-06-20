from ctrade.indicators import *
from ctrade.manager import *
from ctrade.utils import *
from ctrade.messages import *
from model_utils import *
import copy
from collections import OrderedDict
from datetime import datetime
import os
import scipy.stats as st

DATA_FORMAT = "%Y-%m-%d %H:%M"

def clean_dataset(X, Y):

    mask = Y.index.isin(X.index)
    Y = Y[mask]
    mask = X.index.isin(Y.index)
    X = X[mask]
    return X, Y


class StackModels(object):
    
    def __init__(self, estimator):
        self.estimator = estimator
        self.fitted_estimators = []
        self.oob_predictions = []
        self.labels = []
        self.factors = []
        
    def fit(self, X, Y):

        for icol,col in enumerate(Y.columns):
            self.factors.append(Y.iloc[:, icol].std())
            res = do_easy_crossval(self.estimator, X, Y[col]/self.factors[icol],
                                   folds=10, refit=True, plot=False)
            self.fitted_estimators.append(copy.deepcopy(res[1]))
            self.oob_predictions.append(res[0].sort_index()
                                        .rename(columns={k:'{}_{}'.format(k, col) \
                                                         for k in res[0].columns}))
            self.labels.append('pred_{}'.format(col))
            
    def predict(self, X):
    
        predictions = []
    
        for iest,est in enumerate(self.fitted_estimators):
            
            pred = pd.DataFrame(est.predict(X),
                                index=X.index,
                                columns=[self.labels[iest]])
            predictions.append(pred)
            
        return pd.concat(predictions, axis=1)
            
    def stack_predictions(self):
    
        out = self.oob_predictions[0]
        columns = [i for i in out.columns if 'pred' in i]
        out = out[columns]
        for df in self.oob_predictions[1:]:
            columns = [i for i in df.columns if 'pred' in i]
            out = out.join(df[columns], how='inner')
            
        return out.dropna()


class Model(object):
    
    def __init__(self, indicators, currency):
        self.indicators = indicators
        self.currency = currency
        self.indicator_func = OrderedDict()
        
    def set_indicators(self):
        
        def feed(x):
            return {} if x is None else x
        
        for k,v in self.indicators.items():
            if v[0] in ['macd', 'rsi', 'bbands', 'pivot', 'consecutive_periods']:
                self.indicator_func[k] = with_series(self.currency)\
                    (indicator_partial(globals()[v[0]], **feed(v[1])))
            else:
                self.indicator_func[k] = indicator_partial(globals()[v[0]],
                                                           **feed(v[1]))
        
    def get_data(self, df):
        
        return reduce(lambda x,y: pd.concat([x,y], axis=1), 
                      [func(df) for func in self.indicator_func.values()])
    
    def get_target(self, Y, span=[2, 5, 10, 25, 50, 100]):
        
        _Y = pd.DataFrame(index=Y.index)

        for s in span:
            _Y[s] = np.nan
            _Y.iloc[:-s, -1] = (Y - Y.shift(s)).iloc[s:].values
        return _Y


class Signals(object):
    
    def __init__(self, pair):
    
        self.quantiles = {}
        self.cumulative = {}
        self.manager = FileManager(pair)

    def fit(self, X):
        
        for col in X.columns:

            self.cumulative[col] = self.get_cumulative(X[col], st.t)
            df, Q = tag_ranges(X, col, quantiles=(0.3, 0.7))
            self.quantiles[col] = Q

        self.manager.save(self.quantiles, save_type='quantiles')
    
        signal_tags = [i for i in X.columns if 'tag' in i]
        X['main'] = X[signal_tags].sum(axis=1)
        X['signal'] = 0
        mask = X['main'] >3
        X.loc[mask, 'signal'] = 1
        mask = X['main'] <-3
        X.loc[mask, 'signal'] = -1

        return X

    @staticmethod
    def get_cumulative(series, func):

        t_param = func.fit(series)
        distr = func(*t_param)

        return distr.cdf

    @staticmethod
    def apply_tag(df, column, Q):

        df[column+'_tag'] = 0
        mask = df[column]<Q[0]
        df.loc[mask, column+'_tag'] = -1
        mask = df[column]>Q[1]
        df.loc[mask, column+'_tag'] = 1
        
        return df
    
    def predict(self, X):
        
        for col in X.columns:
            
            X = self.apply_tag(X, col, self.quantiles[col])
            
        signal_tags = [i for i in X.columns if 'tag' in i]
        X['main'] = X[signal_tags].sum(axis=1)
        
        X['signal'] = 0
        mask = X['main'] >3
        X.loc[mask, 'signal'] = 1
        mask = X['main'] <-3
        X.loc[mask, 'signal'] = -1

        return X

class Status(object):

    def __init__(self, pair):

        self.pair = pair
        self._status = 'Started'
        self._price = None
        self._time = None
        self.transactions = []
        self.transaction_price = []
        self.manager = FileManager(pair)


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

        date = datetime.now().strftime(DATA_FORMAT)
        if len(self.transactions[-1])==2:
            msg = "{} - Entered {} position for {} at {}\n".format(date,
                                                                 self.status,
                                                                 format_pair(self.pair),
                                                                 self.transaction_price[-1][1])
        else:
            gain =  (self.transaction_price[-1][2] - self.transaction_price[-1][1])\
                     /self.transaction_price[-1][1]*100
            gain = np.round(gain, 3)
            if 'Short' in self.status:
                gain *= -1

            msg = "{} - Closed {} position for {} at {} - {:>7}\n".format(date,
                                                                   self.status.split(' ')[1],
                                                                   format_pair(self.pair),
                                                                   self.transaction_price[-1][1],
                                                                   gain)

        filename = self.manager._home + '/trader-{}.log'.format(self.pair)
        if not os.path.isfile(filename):
            mode = 'w'
        else:
            mode = 'a'
        with open(filename, mode) as f:
            f.write(msg)

        logging.info(msg)
        post_message('cryptobot', msg, username='cryptobot', icon=':matrix:')

    def update(self, last_signal):

        value = last_signal['signal'].iloc[-1]
        price = last_signal[self.pair].iloc[-1]
        timestamp = last_signal.index[-1].strftime("%Y-%m-%d %H:%M")

        if ((self.status=='Started' or 'Close' in self.status) and value==1):
            self.status = 'Long'
            self.transactions.append(['Long', timestamp])
            self.transaction_price.append(['Long', price])
            event = True

        elif (self.status=='Long' and value==-1):
            self.status = 'Close Long'
            self.transactions[-1] += [timestamp]
            self.transaction_price[-1] += [price]
            event = True

        elif ((self.status=='Started' or 'Close' in self.status) and value==-1):
            self.status = 'Short'
            self.transactions.append(['Short', timestamp])
            self.transaction_price.append(['Short', price])
            event = True

        elif (self.status=='Short' and value==1):
            self.status = 'Close Short'
            self.transactions[-1] += [timestamp]
            self.transaction_price[-1] += [price]
            event = True

        else:
            event = False

        if event:
            self.notify()

        self.time = timestamp
        self.price = price