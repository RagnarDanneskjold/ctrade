from matplotlib.finance import candlestick_ohlc
from matplotlib.dates import (
    DateFormatter, WeekdayLocator, DayLocator, MONDAY
)
import pandas as pd
import numpy as np
import copy
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_samples, silhouette_score

def plot_feature_importances(estimator, feature_names, top=None, plot_args=None):

    if hasattr(estimator, 'feature_importances_'):
        feature_importance = estimator.feature_importances_

    elif hasattr(estimator, 'coef_'):
        feature_importance = estimator.coef_
        feature_importance = np.abs(feature_importance)

    if plot_args is not None:
        fig, ax = plt.subplots(1,1, **plot_args)
    else:
        fig, ax = plt.subplots(1,1, figsize=(12,12))

    feature_importance = 100 * (feature_importance / feature_importance.max())

    sorted_idx = np.argsort(-feature_importance)
    
    if top is not None:
        feature_importance = feature_importance[sorted_idx][:top]
        feature_names = feature_names[sorted_idx][:top]
        
    pos = np.arange(len(feature_names)) + 0.5

    ax.barh( pos, feature_importance,  align='center', alpha=0.7)
    ax.set_xlabel("Feature importance [%]")

    ax.set_yticks(pos)
    ax.set_yticklabels( list(feature_names), rotation = 0, alpha=0.5  )

    plt.xlabel('Relative Importance')
    

def plot_candlesticks(data, since=None, ax=None):
    """
    Plot a candlestick chart of the prices,
    appropriately formatted for dates
    """
    # Copy and reset the index of the dataframe
    # to only use a subset of the data for plotting
    df = copy.deepcopy(data)
    if since is not None:
    	df = df[df.index >= since]
    df.reset_index(inplace=True)
    df['date_fmt'] = df['index'].apply(
        lambda date: mdates.date2num(date.to_pydatetime())
    )

    # Set the axis formatting correctly for dates
    # with Mondays highlighted as a "major" tick
    mondays = WeekdayLocator(MONDAY)
    alldays = DayLocator()
    weekFormatter = DateFormatter('%b %d')
    if ax is None:
        fig, ax = plt.subplots(figsize=(16,4))
        fig.subplots_adjust(bottom=0.2)

    ax.xaxis.set_major_locator(mondays)
    ax.xaxis.set_minor_locator(alldays)
    ax.xaxis.set_major_formatter(weekFormatter)

    # Plot the candlestick OHLC chart using black for
    # up days and red for down days

    csticks = candlestick_ohlc(
        ax, df[
            ['date_fmt', 'open', 'high', 'low', 'close']
        ].values, width=0.1, 
        colorup='#1942a0', colordown='#cc1144'
    )
    # ax.set_axis_bgcolor((1,1,0.9))
    
    ax.xaxis_date()
    plt.setp(
        plt.gca().get_xticklabels(), 
        rotation=45, horizontalalignment='right'
    )

def plot_fts(data, column, since=None, ax=None, plot_args={}):
    """
    Plot a candlestick chart of the prices,
    appropriately formatted for dates
    """
    # Copy and reset the index of the dataframe
    # to only use a subset of the data for plotting
    df = copy.deepcopy(data)
    if since is not None:
    	df = df[df.index >= since]

    df.reset_index(inplace=True)
    df['date_fmt'] = df['index'].apply(
        lambda date: mdates.date2num(date.to_pydatetime())
    )

    # Set the axis formatting correctly for dates
    # with Mondays highlighted as a "major" tick
    mondays = WeekdayLocator(MONDAY)
    alldays = DayLocator()
    weekFormatter = DateFormatter('%b %d')
    if ax is None:
        axis = False
        fig, ax = plt.subplots(figsize=(16,4))
        fig.subplots_adjust(bottom=0.2)

    ax.xaxis.set_major_locator(mondays)
    ax.xaxis.set_minor_locator(alldays)
    ax.xaxis.set_major_formatter(weekFormatter)

    # Plot the candlestick OHLC chart using black for
    # up days and red for down days
    df[column].plot(**plot_args)
    ax.xaxis_date()
    # plt.setp(
    #     plt.gca().get_xticklabels(), 
    #     rotation=45, horizontalalignment='right'
    # )

    return ax


def create_follow_cluster_matrix(data):
    """
    Creates a k x k matrix, where k is the number of clusters
    that shows when cluster j follows cluster i.
    """
    k = len(data['Clusters'].unique())
    data["ClusterTomorrow"] = data["Clusters"].shift(-1)
    data.dropna(inplace=True)
    data["ClusterTomorrow"] = data["ClusterTomorrow"].apply(int)
    data["ClusterMatrix"] = list(zip(data["Clusters"], data["ClusterTomorrow"]))
    cmvc = data["ClusterMatrix"].value_counts()
    clust_mat = np.zeros( (k, k) )
    for row in cmvc.iteritems():
        clust_mat[row[0]] = row[1]
	return clust_mat/clust_mat.sum(axis=1).reshape(3,1)


