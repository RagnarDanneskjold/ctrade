from ctrade import *
from datetime import datetime
from ctrade.indicators import *
from model_utils import *
import copy


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
        
    def fit(self, X, Y):
                
        for col in Y.columns:
            res = do_easy_crossval(self.estimator, X, Y[col]*1000, 
                                   folds=10, refit=True, plot=False)
            self.fitted_estimators.append(copy.deepcopy(res[1]))
            self.oob_predictions.append(res[0].sort_index()
                                        .rename(columns={k:'{}_{}'.format(k, col) for k in res[0].columns}))
            self.labels.append('pred_{}'.format(col))
            
    def predict(self, X):
    
        predictions = []
    
        for iest,est in enumerate(self.fitted_estimators):
            
            pred = pd.DataFrame(est.predict(X), index=X.index, columns=[self.labels[iest]])
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
        self.indicator_func = {}
        
    def set_indicators(self):
        
        def feed(x):
            return {} if x is None else x
        
        for k,v in self.indicators.items():
            if v[0] in ['macd', 'rsi', 'bbands', 'pivot', 'consecutive_periods']:
                self.indicator_func[k] = with_series(self.currency)(indicator_partial(globals()[v[0]], **feed(v[1])))
            else:
                self.indicator_func[k] = indicator_partial(globals()[v[0]], **feed(v[1]))
        
    def get_data(self, df):
        
        return reduce(lambda x,y: pd.concat([x,y], axis=1), 
                      [func(df) for func in self.indicator_func.values()])
    
    def get_target(self, Y, span=[2, 5, 10, 25, 50, 100]):
        
        _Y = pd.DataFrame(index=Y.index)

        Y = (Y - Y.mean())/Y.std()

        for s in span:
            _Y[s] = np.nan
            _Y.iloc[:-s, -1] = (Y - Y.shift(s)).iloc[s:].values
        return _Y


class Signals(object):
    
    def __init__(self):
    
        self.quantiles = {}

    def fit(self, X):
        
        for col in X.columns:
            df, Q = tag_ranges(X, col, quantiles=(0.3, 0.7))
            self.quantiles[col] = Q
    
        signal_tags = [i for i in X.columns if 'tag' in i]
        X['main'] = X[signal_tags].sum(axis=1)
        X['signal'] = 0
        mask = X['main'] >3
        X.loc[mask, 'signal'] = 1
        mask = X['main'] <-3
        X.loc[mask, 'signal'] = -1

        return X
    
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
