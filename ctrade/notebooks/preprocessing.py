from sklearn.base import (BaseEstimator,
TransformerMixin)

class MeanScaler(BaseEstimator, TransformerMixin):

    def __init__(self, features=None):

        self.features = features
        self.means = {}
        self.stds = {}

    def fit(self, x, y=None):

        _x = x.copy()

        for col in self.features:

            mask = _x[col].notnull()
            if mask.sum()>1 and len(_x[col].unique())>2:
                mean = _x.loc[mask, col].mean()
                std = _x.loc[mask, col].std()
            else:
                mean = 0
                std = 1
            self.means[col] = mean
            self.stds[col] = std

        return self

    def transform(self, x):

        _x = x.copy()

        for col in self.features:

            mask = _x[col].notnull()
            if mask.sum()>1:
                _x[col] = _x[col].astype(float)
                _x.loc[mask, col] = ((_x.loc[mask, col] - self.means[col])
                                    /self.stds[col])
                _x[col] = _x[col].fillna(0)
            else:
                _x[col] = 0

		return _x