# FusionSolar Northbound Interface Client

Provides a Python API to access Huawei FusionSolar web service to download SmartPVMS data.
To login you need account on Huawei FusionSolar https://eu5.fusionsolar.huawei.com.
Queried data are return as-is. Please refer to Huawei SmartPVMS [Northbound Interface Reference V6](https://support.huawei.com/enterprise/en/doc/EDOC1100261860) documentation for more details about data format.

# Installation

The package is distributed with pip, and can be installed with the command line:

```console
python3 -m pip install pyhfs
```

# Usage

```python
import pyhfs

try:
    with pyhfs.ClientSession(user='user', password='password') as client:
        plants = client.get_plant_list()
        print(plants)
except pyhfs.LoginFailed:
    print('Login failed. Verify user and password of Northbound API account.')
```

For more details about how to use the API, please check [how_to.py](https://github.com/guillaumeblanc/pyhfs/blob/main/how_to.py).

# Running tests

Testing requires a valid Northbound API account, which can be created from [Fusion Solar](https://eu5.fusionsolar.huawei.com) system/company management interface. Tests will look for two environment variables to get user account (FUSIONSOLAR_USER) and password (FUSIONSOLAR_PASSWORD).

Use the following command from directory root to run the tests:
```console
python3 -m unittest discover
```

# Using CI

In case of a fork, these same variables (FUSIONSOLAR_USER and FUSIONSOLAR_PASSWORD) shall be added to github secrets in order for the CI to work.
