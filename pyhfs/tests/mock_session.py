import logging
import os
import sys
import json
import pathlib

# Based on documentation iMaster NetEco V600R023C00 Northbound Interface Reference-V6(SmartPVMS)
# https://support.huawei.com/enterprise/en/doc/EDOC1100261860


class MockSession:
    def __init__(self):
        pass

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.logout()

    def logout(self) -> None:
        pass

    def login(self) -> None:
        pass

    def post(self, endpoint, parameters={}):
        root = pathlib.Path(os.path.dirname(__file__))
        path = root / ('data/' + endpoint + '.json')
        with path.open('rt') as json_file:
            return json.load(json_file)
