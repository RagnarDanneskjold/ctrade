import pandas as pd
from pandas import np
from functools import partial
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def indicator_partial(indicator, **kwargs):
    return partial(indicator, **kwargs)

def with_series(df_column):
    def series_indicator_decorator(indicator):
        def func_wrapper(df, **kwargs):
            return indicator(df[df_column], **kwargs)
        return func_wrapper
    return series_indicator_decorator


def sma(series, window=50, min_periods=0):
    sma = series.rolling(window=window, min_periods=min_periods,
                         center=False).mean()
    sma.rename(index='SMA', inplace=True)
    return sma


def ema(series, window=50, min_periods=0):
    ema = series.ewm(span=window, min_periods=min_periods, adjust=False).mean()
    ema.rename(index='EMA', inplace=True)
    return ema


def macd(series, fast_window=12, slow_window=26, signal_window=9):

    logging.info('Calculating macd')
    macd = ema(series, window=fast_window) - ema(series, window=slow_window)
    signal = ema(macd, window=signal_window)
    return pd.DataFrame({'macd_{}-{}'.format(fast_window, slow_window): macd, 
                         'macd_signal_{}-{}'.format(fast_window, slow_window): signal})


def tag_ranges(df, column, quantiles=(0.1, 0.9)):
	m = df[column].quantile(quantiles[0])
	M = df[column].quantile(quantiles[1])
	Q1 = df[column].quantile(0.55)
	Q2 = df[column].quantile(0.45)

	df[column+'_tag'] = 0
	mask = df[column]>=M
	df.loc[mask, column+'_tag'] = 1
	mask = df[column]<=m
	df.loc[mask, column+'_tag'] = -1
	# mask = (df[column]<=Q1) & (df[column]>=Q2)
	# df.loc[mask, column+'_tag'] = 2
	return df, (m, M)

def which_q(df, column, value):

	x = (df.sort_values(column, ascending=True)[column] - value)>0*1
	return x!=x.shift(1)


def stoc(df, col_labels=('low', 'high', 'close'),
         k_smooth=0, d_smooth=3, window=14, min_periods=0):
    # Should col_labels be a dictionary? i.e. {'low':'Low', ...}
    low = df[col_labels[0]]
    high = df[col_labels[1]]
    close = df[col_labels[2]]

    # min_periods should always be 0 for this
    lowest_low = low.rolling(window=window, min_periods=0).min()
    highest_high = high.rolling(window=window, min_periods=0).max()

    k = (close - lowest_low) / (highest_high - lowest_low) * 100

    if min_periods > 0:
        k[:min_periods] = np.NaN

    if k_smooth != 0:
        k = sma(k, window=k_smooth)
    d = sma(k, window=d_smooth)

    return pd.DataFrame({'%K_{}'.format(window): k, '%D_{}'.format(window): d})


def fstoc(df, col_labels=('low', 'high', 'close'),
          k_smooth=0, d_smooth=3, window=14):
    return stoc(df, col_labels=col_labels, k_smooth=k_smooth,
                d_smooth=d_smooth, window=window, min_periods=0)


def sstoc(df, col_labels=('low', 'high', 'close'),
          k_smooth=3, d_smooth=3, window=14):
    return stoc(df, col_labels=col_labels, k_smooth=k_smooth,
                d_smooth=d_smooth, window=window, min_periods=0)


def atr(df, col_labels=('low', 'high', 'close'), window=14):

    logging.info('Calculating atr')
    low = df[col_labels[0]]
    high = df[col_labels[1]]
    close = df[col_labels[2]]

    tr_1 = high - low
    tr_2 = (high - close.shift()).abs()  # High - Previous Close
    tr_3 = (low - close.shift()).abs()

    max_tr = pd.concat([tr_1, tr_2, tr_3], axis=1).max(axis=1)

    atr = pd.Series(0.0, index=max_tr.index, name='ATR')
    atr[:window-1] = np.NaN
    atr[window-1] = max_tr[:window].mean()

    for i in range(window, len(atr)):
        atr[i] = (atr[i - 1] * (window - 1) + max_tr[i]) / window

    return atr.to_frame('atr_{}'.format(window))


def bbands(series, window=20, min_periods=0, stdev_multiplier=2, mode='ranges'):

    logging.info('Calculating bolinger bands')
    middle = sma(series, window=window, min_periods=min_periods)
    std = series.rolling(window=window,
                         min_periods=min_periods).std() * stdev_multiplier
    std.iloc[0] = 0.0  # We define the std of one element to be 0
    upper = middle + std
    lower = middle - std
    if mode=='ranges':
        return pd.DataFrame({'bbands_lower_{}'.format(window): lower,
                             'bbands_middle_{}'.format(window): middle,
                             'bbands_upper_{}'.format(window): upper})
    elif mode=='spread':
        return pd.DataFrame({'bbands_{}'.format(window): (upper-lower)/middle})


def rsi(series, window=14, min_periods=0):

    logging.info('Calculating stocastic oscillator')
    change = series.diff()
    change.iloc[0] = 0.0  # Set gain/loss of first day to zero
    # Using arithmetic mean, not exponential smoothing here
    avg_up = (change.where(change > 0, other=0.0)
                    .rolling(window=window, min_periods=min_periods)
                    .mean())
    avg_down = (change.where(change < 0, other=0.0)
                      .abs()
                      .rolling(window=window, min_periods=min_periods)
                      .mean())
    rsi = avg_up / (avg_up + avg_down) * 100
    # If avg_up+avg_down = 0 the rsi should be around 50... I think
    rsi.replace(to_replace=[np.inf, np.NaN], value=50, inplace=True)
    if min_periods > 0:
        rsi[:min_periods-1] = np.NaN
    rsi.rename(index='RSI', inplace=True)
    return rsi.to_frame('rsi_{}'.format(window))


def get_pivot(x, mode='day'):
    if mode=='day':
        x[mode] = x.reset_index()['index'].apply(lambda x: x.dayofyear).values
        logging.info('Calculating daily pivot levels')
    if mode=='week':
        x[mode] = x.reset_index()['index'].apply(lambda x: x.week).values
        logging.info('Calculating weekly pivot levels')

    close = x.groupby([mode]).last()['value'].sort_index()
    high = x.groupby([mode]).aggregate(np.max)['value'].sort_index()
    low = x.groupby([mode]).aggregate(np.min)['value'].sort_index()

    pivot = ((high+low+close)/3).to_frame('P')

    r1 = (2*pivot['P'] - low).to_frame('R1')
    s1 = (2*pivot['P'] - high).to_frame('S1')
    r2 = (pivot['P'] - s1['S1'] + r1['R1']).to_frame('R2')
    s2 = (pivot['P'] - (r1['R1'] - s1['S1'])).to_frame('S2')
    r3 = (pivot['P'] - s2['S2'] + r2['R2']).to_frame('R3')
    s3 = (pivot['P'] - (r2['R2'] - s2['S2'])).to_frame('S3')
    
    return reduce(lambda x,y: pd.concat([x,y], axis=1), [pivot, r1, s1, r2, s2, r3, s3] )


def pivot(series, mode='day'):
    x = series.to_frame('value')
    p = get_pivot(x, mode)
    if mode=='week':
        x[mode] = x.reset_index()['index'].apply(lambda x: x.week).values
    elif mode=='day':
        x[mode] = x.reset_index()['index'].apply(lambda x: x.dayofyear).values

    groups = x.groupby([mode])
    out = pd.DataFrame()
    levels = ['{}_{}_diff'.format(i, mode) for i in p.columns ]

    for igroup, group in groups:
        ref = igroup-1
        for i in levels:
            if ref in p.index:
                group.loc[:,i] = group.loc[:,'value'] - p.loc[ref, i.split('_')[:1]].values[0]
            else:    
                group.loc[:,i] =  np.nan

        out = pd.concat([out, group])
        
    return out[levels]


def consecutive(series):
    series_up = (series - series.shift(1)).copy()
    series_down = (series.shift(1) - series).copy()
    y_up = series_up.apply(lambda x: 1 if x>0 else 0)
    y_up = (y_up * (y_up.groupby((y_up != y_up.shift()).cumsum()).cumcount() + 1)).to_frame('conseq_up')
    y_down = series_down.apply(lambda x: 1 if x>0 else 0)
    y_down = (y_down * (y_down.groupby((y_down != y_down.shift()).cumsum()).cumcount() + 1)).to_frame('conseq_down')
    return y_up.join(y_down)


def consecutive_periods(series, add_periods):
    y = consecutive(series)
    for period in add_periods:
        resampled = series.resample(period)
        resampled_gains = consecutive(resampled)
        y = y.join(resampled_gains.rename(columns={'conseq_up': 'conseq_up_{}'.format(period),
                                                   'conseq_down': 'conseq_down_{}'.format(period)}
                                                   ), 
                    how='left')
        y['conseq_up_{}'.format(period)] = y['conseq_up_{}'.format(period)].fillna(method='ffill')
        y['conseq_down_{}'.format(period)] = y['conseq_down_{}'.format(period)].fillna(method='ffill')

    return y 
