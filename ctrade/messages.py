
"""This module provides functions for interacting with the SCL Group slack."""

from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

import json

import requests
import six

from . import config
from . import core

if six.PY2:
    from contextlib2 import contextmanager
else:
    from contextlib import contextmanager


def post_message(channel, message, username='cryptobot', icon=':ghost:',
                 alert_users=None, alert_channel=False):

    """Post a message to an slack Group slack channel or user.
    Parameters
    ----------
    channel : str
        Channel or user to message. Channels are named with a leading ``#``,
        users with a leading ``@``.
    message : str
        The message to post, see the ``Notes`` section for syntax.
    username : str, optional
        Username for the message to come from.
        Default is ``'scl-bot'``.
    icon : str, optional
        User icon for the post to have. See http://www.emoji-cheat-sheet.com
        for options.
        Default is ``':ghost:'``.
    alert_users : str or list of str, optional
        Users to alert. Single slack username or a list.
        The leading ``@`` is optional.
        Default behaviour alerts no users.
    alert_channel : bool, optional
        Whether to alert the entire channel posted in.
        Default behaviour does not alert the channel.
    Examples
    --------
    The following example would post in the ``#data`` channel alerting ``@foo``
    and ``@bar``:
    >>> channel = '#data'
    >>> message = 'Do I have your attention?'
    >>> alert_users = ['foo', 'bar']
    >>> post_message(channel, message, alert_users=alert_users)
    The message would look like this::
        @foo @bar Do I have your attention?
    It is possible to direct message a user:
    >>> post_message(channel='@foo', message='I have your attention.')
    Notes
    -----
    Slack can parse the message and tag users, channels and commands. The
    syntax is as follows:
    * User: ``<@username>``
    * Channel: ``<#channel-name>``
    * Command: ``<!command-name>`` (e.g. ``<!channel>`` or ``<!group>`` to
      notify the entire channel being posted to)
    Slack automatically marks-up urls.
    For more advanced formatting see https://api.slack.com/docs/formatting
    """
    raw_config = config.load_config()
    slack_dict = config.extract_value(raw_config, 'slack', 'main')
    slack_url = config.extract_value_set_type(slack_dict, 'webhook_url',
                                              'slack', str)
    alert_string = _alert_string(alert_users, alert_channel)
    alert_message = alert_string + message

    json_dict = {
        'username': username,
        'channel': channel,
        'text': alert_message,
        'icon_emoji': icon
    }

    return requests.post(slack_url, data=json.dumps(json_dict))


@contextmanager
def post_error(channel, alert_users=None, alert_channel=False,
               message=None, username='runtime-error', icon=':exclamation:'):
    """Context manager or decorator to post exceptions to slack.
    The original exception is still raised in the python process.
    The message posted in the channel can alert the whole channel as well as
    specific users. The last line of the error message (not the whole
    traceback) is also included in the message.
    Parameters
    ----------
    channel : str
        Channel or user to message. Channels are named with a leading ``#``,
        users with a leading ``@``.
    alert_users : str or list of str, optional
        Users to alert if an error is raised. Single slack username or a list.
        The leading ``@`` is optional.
        Default behaviour alerts no users.
    alert_channel : bool, optional
        Whether to alert the entire channel posted in.
        Default behaviour does not alert the channel.
    message : str, optional
        The message to post ahead of the error message. For example it may be
        useful to post details about the script that was running.
        Default behaviour posts ``'Runtime error:'``.
    username : str, optional
        Username for the message to come from.
        Default is ``'runtime-error'``.
    icon : string, optional
        User icon for the post to have. See http://www.emoji-cheat-sheet.com
        for options.
        Default is ``':exclamation:'``.
    Examples
    --------
    The following example would post in the ``#data`` channel alerting
    ``@foo`` and ``@bar``:
    >>> with post_error('#data', ['foo', 'bar'], message="Don't Panic"):
    ...     raise TypeError('Panic')
    The message would look like this::
        @foo @bar Don't Panic:
        `TypeError: Panic`
    The following example would alert ``@user`` directly:
    >>> @post_error('@user', message="Don't Panic")
    ... def raise_type():
    ...     raise TypeError('Panic')
    >>> raise_type()
    The message would be similar, only lacking the direct alerts of ``@foo``
    and ``@bar``.
    """
    try:
        yield
    except Exception as e:
        _post_error(channel, e, alert_users, alert_channel,
                    message, username, icon)
        raise(e)


def _post_error(channel, error, alert_users=None, alert_channel=False,
                message=None, username='runtime-error',
                icon=':exclamation:'):
    msg = _construct_error_message(error, alert_users, alert_channel,
                                   message)

    post_message(channel, msg, username, icon, alert_users, alert_channel)


def _construct_error_message(error, alert_users, alert_channel, message):
    message = message if message else 'Runtime error'
    if not message.endswith(':'):
        message = message + ':'

    t = type(error).__name__
    m = "{m}\n`{t}: {e}`".format(m=message, t=t, e=error)

    return m


def _alert_string(alert_users, alert_channel):
    users_formatted = _format_users(alert_users)
    channel_formatted = _format_channel(alert_channel)
    alert_strings = [channel_formatted, users_formatted]
    alert_strings = [s for s in alert_strings if s]

    if alert_strings:
        alert_string = ' '.join(alert_strings) + ' '
    else:
        alert_string = ''

    return alert_string


def _format_users(alert_users):
    if alert_users:
        users = core.cast_as_array(alert_users)
        prepended_at = ['@' + u if not u.startswith('@') else u for u in users]

        return '<{}>'.format('> <'.join(prepended_at))


def _format_channel(alert_channel):
    return '<!channel>' if alert_channel else None