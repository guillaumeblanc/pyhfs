import unittest

from pyhfs.tests.utils import credentials, no_credentials, frequency_limit
import pyhfs


class TestSession(unittest.TestCase):
    @classmethod
    @frequency_limit
    def setUpClass(cls):
        cls.invalid = "Invalid93#!"
        if no_credentials():
            cls.user, cls.password = None, None
        else:
            cls.user, cls.password = credentials()

    @classmethod
    def tearDownClass(cls):
        pass

    @unittest.skipIf(no_credentials(), "Credentials not provided")
    @frequency_limit
    def test_invalid_user(self):
        with self.assertRaises(pyhfs.LoginFailed):
            with pyhfs.Session(user=self.invalid, password=self.invalid):
                pass

    @unittest.skipIf(no_credentials(), "Credentials not provided")
    @frequency_limit
    def test_invalid_password(self):
        with self.assertRaises(pyhfs.LoginFailed):
            with pyhfs.Session(user=self.user, password=self.invalid):
                pass

    @unittest.skipIf(no_credentials(), "Credentials not provided")
    @frequency_limit
    def test_valid_login(self):
        with pyhfs.Session(user=self.user, password=self.password):
            pass


if __name__ == "__main__":
    unittest.main()
