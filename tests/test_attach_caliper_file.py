#!/usr/bin/env python
from nose.tools import assert_almost_equal, assert_equal, assert_true, assert_raises
from os.path import isdir
import os
import sys
import subprocess

from genologics.lims import Lims
from genologics.config import BASEURI,USERNAME,PASSWORD
from genologics.scripts.attach_caliper_files import process_from_file_name, NotFoundError

class test_all(object):
    def setUp(self):
        self.lims = Lims(BASEURI,USERNAME,PASSWORD)
        self.lims.check_version()

    def tearDown(self):
        pass

    def test_name_not_id(self):
        fn= 'P671P1_A1_P671_101_info_A1.png'
        with assert_raises(NotFoundError) as cm:
            process_from_file_name(fn,self.lims)
        e = cm.exception

        s = ("No Container found with query key 'id' and query value 'P671P1', "
        "parsed from file name P671P1_A1_P671_101_info_A1.png.")
        assert_equal(str(e),s)





