from unittest import TestCase
from xml.etree import ElementTree
from sys import version_info
if version_info.major == 2:
    from mock import patch, Mock
    import __builtin__ as builtins
else:
    from unittest.mock import patch, Mock
    import builtins


from genologics.entities import StringDescriptor, StringAttributeDescriptor


class TestEntities(TestCase):

    def test_pass(self):
        pass


class TestDescriptor(TestCase):

    def _make_desc(self, klass, *args, **kwargs):
        return klass(*args, **kwargs)


class TestStringDescriptor(TestDescriptor):
    url = 'http://testgenologics.com:4040'

    def setUp(self):
        self.et = ElementTree.fromstring("""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<sample>
<name>test sample</name>
</sample>
""".format(url=self.url))
        self.instance = Mock(root=self.et)

    def test__get__(self):
        sd = self._make_desc(StringDescriptor, 'name')
        assert sd.__get__(self.instance, None) == "test sample"

    def test__set__(self):
        sd = self._make_desc(StringDescriptor, 'name')
        sd.__set__(self.instance, "new test sample")
        assert self.et.find('name').text == "new test sample"


class TestStringAttributeDescriptor(TestDescriptor):
    url = 'http://testgenologics.com:4040'

    def setUp(self):
        self.et = ElementTree.fromstring("""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<container-type name="test container">
</container-type>""")
        self.instance = Mock(root=self.et)

    def test__get__(self):
        sd = self._make_desc(StringAttributeDescriptor, 'name')
        assert sd.__get__(self.instance, None) == "test container"



