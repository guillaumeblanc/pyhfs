import os
import sys
import logging
import functools

import pyhfs


def frequency_limit(func):
    '''Handle frequency limits cases, which cannot ben considered as fails.'''
    @functools.wraps(func)
    def wrap(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except pyhfs.FrequencyLimit:
            logging.warning(
                'Couldn\'t complete test due to exceeding frequency limits.')
    return wrap


def credentials():
    user = os.environ.get('FUSIONSOLAR_USER')
    if user is None:
        raise ValueError('Missing environment variable FUSIONSOLAR_USER')

    password = os.environ.get('FUSIONSOLAR_PASSWORD')
    if password is None:
        raise ValueError('Missing environment variable FUSIONSOLAR_PASSWORD')

    return user, password
