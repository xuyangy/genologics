import xml
from unittest import TestCase


from genologics.lims import Lims


from sys import version_info
if version_info.major == 2:
    from mock import patch, Mock
else:
    from unittest.mock import patch, Mock

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
        #TODO: create serialized xml pass it to put and test that it get passed on correctly
        pass


    @patch('requests.post', return_value=Mock(content = sample_xml, status_code=200))
    def test_post(self, mocked_instance):
        lims = Lims(self.url, username=self.username, password=self.password)
        #TODO: create serialized xml pass it to post and test that it get passed on correctly
        pass


    @patch('os.path.isfile', return_value=True)
    def test_upload_new_file(self, mocked_instance):
        lims = Lims(self.url, username=self.username, password=self.password)
        xml_intro = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>"""
        file_start = """<file:file xmlns:file="http://genologics.com/ri/file">"""
        file_start2 = """<file:file xmlns:file="http://genologics.com/ri/file" uri="{url}/api/v2/files/40-3501" limsid="40-3501">"""
        attached = """    <attached-to>{url}/api/v2/samples/test_sample</attached-to>"""
        upload = """    <original-location>filename_to_upload</original-location>"""
        content_loc = """    <content-location>sftp://{url}/opt/gls/clarity/users/glsftp/clarity/samples/test_sample/test</content-location>"""
        file_end = """</file:file>"""
        glsstorage_xml = '\n'.join([xml_intro,file_start, attached, upload, content_loc, file_end]).format(url=self.url)
        file_post_xml = '\n'.join([xml_intro, file_start2, attached, upload, content_loc, file_end]).format(url=self.url)
        with patch('requests.post', side_effect=[Mock(content=glsstorage_xml, status_code=200),
                                                 Mock(content=file_post_xml, status_code=200),
                                                 Mock(content=file_post_xml, status_code=200)]):

            lims.upload_new_file(Mock(uri=self.url+"/api/v2/samples/test_sample"),
                                 'filename_to_upload')



    def test_tostring(self):
        lims = Lims(self.url, username=self.username, password=self.password)
        from xml.etree import ElementTree as ET
        a = ET.Element('a')
        b = ET.SubElement(a, 'b')
        c = ET.SubElement(a, 'c')
        d = ET.SubElement(c, 'd')
        etree = ET.ElementTree(a)
        expected_string=b"""<a><b /><c><d /></c></a>"""
        string = lims.tostring(etree)
        assert string == expected_string

