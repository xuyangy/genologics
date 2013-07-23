
#!/usr/bin/env python
from nose.tools import assert_almost_equal, assert_equal, assert_true, assert_raises
import os
import sys

from genologics.lims import Lims
from genologics.config import BASEURI,USERNAME,PASSWORD
from genologics.scripts.attach_caliper_files import artifact_from_file_name, NotFoundError

class test_all(object):
    def setUp(self):
        self.lims = Lims(BASEURI,USERNAME,PASSWORD)
        self.lims.check_version()

    def tearDown(self):
        pass

    def test_wrong_container_id(self):
        fn= 'P671P1_A1_P671_101_info_A1.png'
        with assert_raises(NotFoundError) as cm:
            artifact_from_file_name(fn,self.lims)
        e = cm.exception

        s = ("No Container found with query key 'id' and query value 'P671P1', "
        "parsed from file name P671P1_A1_P671_101_info_A1.png.")
        assert_equal(str(e),s)


    def test_correct_artifact(self):
        fn='27-4562_A1_P601_101_A1.png'
        a = artifact_from_file_name(fn,self.lims)
        assert_equal(a.id,'92-62704')
        fn= '27-1893_E2_P189_113_info_L9.png'
        a = artifact_from_file_name(fn,self.lims)
        assert_equal(a.id,'92-13345')
        fn='27-4118_A1_P671_101_info_A1.png'
        a = artifact_from_file_name(fn,self.lims)
        assert_equal(a.id,'92-59566')

