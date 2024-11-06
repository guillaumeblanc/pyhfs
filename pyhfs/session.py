import logging
import requests
import json
import functools

from . import exception

logger = logging.getLogger(__name__)

# Based on documentation iMaster NetEco V600R023C00 Northbound Interface Reference-V6(SmartPVMS)
# https://support.huawei.com/enterprise/en/doc/EDOC1100261860


def exceptions_sanity(func):
    """Ensures sanity of exceptions raised to the public API. No internal exception should get to public side."""

    @functools.wraps(func)
    def wrap(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except exception._InternalException as e:
            logger.exception("Internal exceptions getting out of of the private code.")
            raise exception.Exception(e.args[0], e.args[1]) from None

    return wrap


class Session:
    """
    Instantiate a session that'll login to Fusion Solar Northbound interface and allow to post requests.
    Errors are reported as exceptions. See exception.py for all public exceptions.
    Huawei Northbound interface address can be change to adapt to different location. Base address is https://eu5.fusionsolar.huawei.com.
    """

    def __init__(self, user: str, password: str, base_url="https://eu5.fusionsolar.huawei.com"):
        self.user = user
        self.password = password
        self.base_url = base_url + "/thirdData/"
        self.session = requests.session()
        self.session.headers.update({"Connection": "keep-alive", "Content-Type": "application/json"})

    @exceptions_sanity
    def __enter__(self):
        self.login()
        return self

    @exceptions_sanity
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.logout()
        self.session.close()

    @exceptions_sanity
    def logout(self) -> None:
        """Logout from base url"""
        try:
            logger.debug("Logout request")
            self._raw_post("logout")
        except exception._305_NotLogged:
            # Expected to happen after logout
            pass

    @exceptions_sanity
    def login(self) -> None:
        """
        Login to base url
        See documentation: https://support.huawei.com/enterprise/en/doc/EDOC1100261860/9e1a18d2/login-interface
        """
        try:
            # Posts login request
            self.session.cookies.clear()
            logger.debug("Login request")
            response, body = self._raw_post(
                endpoint="login", parameters={"userName": self.user, "systemCode": self.password}
            )
            # Login succeeded, stores authentication token
            self.session.headers.update(
                {"XSRF-TOKEN": response.headers.get("XSRF-TOKEN") or response.cookies.get(name="XSRF-TOKEN")}
            )
        except exception._305_NotLogged:
            # Login failed can also be raised directly for 20001, 20002, 20003 failCodes.
            raise exception.LoginFailed() from None
        except json.JSONDecodeError:
            # FusionSolar NBI sends an empty json when user is unknown. It's not the expected behavior described by documentation 7.1.1.
            # It's caught here with JSONDecodeError exception.
            raise exception.LoginFailed() from None

    @exceptions_sanity  # Must be the first decorator.
    def post(self, endpoint, parameters={}):
        """
        Executes a POST request for the current session.
        Automatically logs in the user if he's not logged in yet.
        Validates response is a success, otherwise throws a fusnic.Exception
        """
        login_again = False
        while True:
            if login_again:
                self.login()
            try:
                response, body = self._raw_post(endpoint, parameters)
                return body
            except exception._305_NotLogged:
                login_again = True

    def _raw_post(self, endpoint, parameters={}) -> requests.Response:
        """
        Executes a POST request for the current session.
        Validates response is a success, otherwise throws a fusnic.Exception
        """
        logger.debug(f"POST {self.base_url + endpoint}, parameters {json.dumps(parameters)}")
        response = self.session.post(url=self.base_url + endpoint, json=parameters)
        response.raise_for_status()
        body = response.json()
        if not body.get("success", False):
            raise exception._FailCodeToException(body)
        return response, body
