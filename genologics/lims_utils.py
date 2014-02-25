#!/usr/bin/env python

from genologics.epp import EppLogger

import logging
import sys

from shutil import copy
import os

from time import strftime, localtime
from requests import HTTPError

def get_run_info(fc):
	fc_summary={}
	for iom in fc.input_output_maps:
		art = iom[0]['uri']
		lane = art.location[1].split(':')[0]
		if not fc_summary.has_key(lane):
     			fc_summary[lane]= dict(art.udf.items()) #"%.2f" % val ----round??
	return fc_summary







