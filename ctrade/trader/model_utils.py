from collections import OrderedDict
from sklearn.model_selection import (KFold, StratifiedKFold)
from sklearn.feature_selection import (f_classif, f_regression,
                                       SelectPercentile)
from sklearn.dummy import DummyClassifier, DummyRegressor
import pandas as pd


def do_easy_crossval(estimator, X, Y, transformer=None, W=None, 
                     refit=True, plot=True, folds=5):

    kf = ModelType(estimator).cv(n_splits=folds, shuffle=True)
    modeltype = ModelType(estimator)._modeltype
    Y_score = OrderedDict(); Yte = OrderedDict(); Y_pred = OrderedDict(); i=0
    Wte = OrderedDict()
    crossval_prediction = pd.DataFrame(0, index=X.index, columns=['true', 'pred', 'proba'])
    crossval_prediction['true'] = Y.values
    folds = 1

    split = kf.split(X) if modeltype=='regressor' else kf.split(X,Y)

    for train_index, test_index in split:
        Xtr, Xte = X.iloc[train_index,:], X.iloc[test_index,:]
        Ytr, Yte[i] = Y.iloc[train_index], Y.iloc[test_index]
        if W is not None:
            Wtr, Wte[i] = W.iloc[train_index], W.iloc[test_index]
        if transformer is not None:
            Xtr = transformer.fit_transform(Xtr, Ytr)
            Xte = transformer.transform(Xte)
        if W is not None:
            estimator.fit(Xtr, Ytr, sample_weight=Wtr.values.ravel())
        else:
            estimator.fit(Xtr, Ytr)
        crossval_prediction.iloc[test_index, 1] = estimator.predict(Xte)

        if modeltype == 'classifier':
            crossval_prediction.iloc[test_index, 2] = estimator.predict_proba(Xte)[:,1]

        if plot:
            print 'Trained fold {}'.format(folds)
        folds += 1
        
    if not refit:
        return crossval_prediction
    else:
        if transformer is not None:
            X = transformer.fit_transform(X, Y)
        estimator.fit(X, Y, W)
        
    return crossval_prediction, estimator, transformer, X.columns


class ModelType(object):
    def __init__(self, estimator):
        self.estimator = estimator
        self._modeltype = estimator._estimator_type

    def set_columns(self):
        if self._modeltype == 'classifier':
            return ['true', 'pred', 'prob']
        elif self._modeltype == 'regressor':
            return ['true', 'pred']
        else:
            raise ValueError('Type not supported')

    @property
    def modeltype(self):
        return self._modeltype

    @modeltype.setter
    def modeltype(self, estimator):
        self._modeltype = estimator._estimator_type

    @property
    def cv(self):
        if self._modeltype == 'classifier':
            return StratifiedKFold
        elif self._modeltype == 'regressor':
            return KFold
        else:
            raise ValueError('Type not supported')

    @property
    def anova(self):
        if self._modeltype == 'classifier':
            return f_classif
        elif self._modeltype == 'regressor':
            return f_regression
        else:
            raise ValueError('Type not supported')

    @property
    def dummy(self):
        if self._modeltype == 'classifier':
            return DummyClassifier
        elif self._modeltype == 'regressor':
            return DummyRegressor
        else:
            raise ValueError('Type not supported')