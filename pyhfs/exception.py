import logging

# Based on documentation iMaster NetEco V600R023C00 Northbound Interface Reference-V6(SmartPVMS)
# https://support.huawei.com/enterprise/en/doc/EDOC1100261860/787d54d9/error-code-list


# Public API exception

class Exception(Exception):
    '''Undefined Fusion exception'''


class LoginFailed(Exception):
    '''Login failed. Verify user and password of Northbound API account.'''


class FrequencyLimit(Exception):
    '''(407) The interface access frequency is too high.'''


class Permission(Exception):
    '''(401) You do not have the related data interface permission.'''


# Internal exceptions, should not get out of module implementation

class _InternalException(Exception):
    '''Undefined internal fusion exception'''


class _305_NotLogged(_InternalException):
    '''You are not in the login state. You need to log in again.'''


def _FailCodeToException(body):
    # Any exception to return to user space must be properly declared in the switcher,
    # otherwise an _InternalException exception is returned.
    switcher = {
        305: _305_NotLogged,  # You are not in the login state.
        401: Permission,  # You do not have the related interface permission.
        407: FrequencyLimit,  # The interface access frequency is too high.
        20001: LoginFailed,  # The third-party system ID does not exist.
        20002: LoginFailed,  # The third-party system is forbidden.
        20003: LoginFailed,  # The third-party system has expired.
        # The username or password of the third-party system is incorrect.
        # - The user is locked.
        # - The password has expired.
        # - The number of online sessions reaches the upper limit.
        20400: LoginFailed,
        20618: FrequencyLimit,  # Maximum number of calls per user per day.
        30029: LoginFailed,  # Authentication failed.
    }

    # Returns the exception matching failCode, or _InternalException by default
    failCode = body.get('failCode', 0)
    logging.debug('failCode ' + str(failCode) +
                  ' received with body: ' + str(body))
    message = body.get('message', None)
    return switcher.get(failCode, _InternalException)(failCode, message if message else 'No error message.')
