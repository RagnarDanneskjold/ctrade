import pandas as pd
import numpy as np

def moving_avereage(df, column, period=5):
    df[column+'_ewma{}'.format(period)] = df[column].ewm(span=period).aggregate(np.mean)
    return df

def moving_average_convergence(df, column, nslow=26, nfast=12, normed=True):

	label = 'macd_{}-{}'.format(nfast, nslow)
	df = moving_avereage(df, column, period=nslow)
	df = moving_avereage(df, column, period=nfast)
	df[label] = df[column+'_ewma{}'.format(nfast)] - \
				df[column+'_ewma{}'.format(nslow)]
	if normed:
		df[label] = (df[label] - df[label].mean())/df[label].std()
	return df

def tag_ranges(df, column, quantiles=(0.1, 0.9)):
	m = df[column].quantile(quantiles[0])
	M = df[column].quantile(quantiles[1])
	print(m, M)
	Q1 = df[column].quantile(0.55)
	Q2 = df[column].quantile(0.45)

	df[column+'_tag'] = 0
	mask = df[column]>=M
	df.loc[mask, column+'_tag'] = -1
	mask = df[column]<=m
	df.loc[mask, column+'_tag'] = 1
	mask = (df[column]<=Q1) & (df[column]>=Q2)
	df.loc[mask, column+'_tag'] = 2
	return df, (m, M)

def which_q(df, column, value):

	x = (df.sort_values(column, ascending=True)[column] - value)>0*1
	return x!=x.shift(1)


def relative_strength(prices, n=14):
    """
    compute the n period relative strength indicator
    http://stockcharts.com/school/doku.php?id=chart_school:glossary_r#relativestrengthindex
    http://www.investopedia.com/terms/r/rsi.asp
    """

    deltas = np.diff(prices)
    seed = deltas[:n+1]
    up = seed[seed >= 0].sum()/n
    down = -seed[seed < 0].sum()/n
    rs = up/down
    rsi = np.zeros_like(prices)
    rsi[:n] = 100. - 100./(1. + rs)

    for i in range(n, len(prices)):
        delta = deltas[i - 1]  # cause the diff is 1 shorter

        if delta > 0:
            upval = delta
            downval = 0.
        else:
            upval = 0.
            downval = -delta

        up = (up*(n - 1) + upval)/n
        down = (down*(n - 1) + downval)/n

        rs = up/down
        rsi[i] = 100. - 100./(1. + rs)

    return rsi
