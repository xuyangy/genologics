import unittest
from genologics.lims import *
from mock import patch, Mock, MagicMock

TEST_USER = "test-user"
TEST_PASSWORD = "test-password"
TEST_BASEURI = "http://example.com:8080"
TEST_VERSION = "v2"
TEST_URI = TEST_BASEURI + "/api/" + TEST_VERSION + "/processes"

class TestClientBasics(unittest.TestCase):
    
    def setUp(self):
        self.lims = Lims(TEST_BASEURI, TEST_USER, TEST_PASSWORD, TEST_VERSION)
        

    def tearDown(self):
        pass


    def test_uri(self):
        uri_result = self.lims.get_uri("processes")
        self.assertEqual(TEST_URI, uri_result)


    def test_get(self):
        self.lims.request_session.get = MagicMock(return_value="")
        self.lims.get(TEST_URI)
        



