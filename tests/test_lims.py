import xml
from unittest import TestCase
from genologics.lims import Lims
from unittest.mock import Mock
from unittest.mock import patch


class TestLims(TestCase):
    url = 'http://testgenologics.com:4040'
    username = 'test'
    password ='password'
    sample_xml = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<smp:samples xmlns:smp="http://genologics.com/ri/sample">
    <sample uri="{url}/api/v2/samples/test_sample" limsid="test_id"/>
</smp:samples>
""".format(url=url)


    def test_get_uri(self):
        lims = Lims(self.url, username=self.username, password=self.password)
        assert lims.get_uri('artifacts',sample_name='test_sample') == '{url}/api/v2/artifacts?sample_name=test_sample'.format(url=self.url)


    def test_parse_response(self):
        lims = Lims(self.url, username=self.username, password=self.password)
        r = Mock(content = self.sample_xml, status_code=200)
        pr = lims.parse_response(r)
        assert isinstance(pr, xml.etree.ElementTree.Element)
        #TODO: uncomment when HTTPError can be reach when message in not set in xml or Mock the expected xml message
        #r = Mock(content = content, status_code=400)
        #self.assertRaises(lims.parse_response(r), requests.exceptions.HTTPError)


    @patch('requests.Session.get',return_value=Mock(content = sample_xml, status_code=200))
    def test_get(self, mocked_instance):
        lims = Lims(self.url, username=self.username, password=self.password)
        r = lims.get('{url}/api/v2/artifacts?sample_name=test_sample'.format(url=self.url))
        assert isinstance(r, xml.etree.ElementTree.Element)
        assert mocked_instance.call_count == 1
        mocked_instance.assert_called_with('http://testgenologics.com:4040/api/v2/artifacts?sample_name=test_sample', timeout=16,
                                  headers={'accept': 'application/xml'}, params={}, auth=('test', 'password'))

    @patch('requests.put', return_value=Mock(content = sample_xml, status_code=200))
    def test_put(self, mocked_instance):
        lims = Lims(self.url, username=self.username, password=self.password)
        #TODO: create serialized xml pass it to put and test that it get past on correctly
        # pass


    @patch('requests.post', return_value=Mock(content = sample_xml, status_code=200))
    def test_post(self, mocked_instance):
        lims = Lims(self.url, username=self.username, password=self.password)
        #TODO: create serialized xml pass it to post and test that it get past on correctly
        pass

