#!/usr/bin/env python

from genologics.epp import EppLogger

import logging
import sys

from shutil import copy
import os

from time import strftime, localtime
from requests import HTTPError

class CopyField(object):
    """Class to copy any filed (or udf) from any lims element to any 
    udf on any other lims element

    argumnets:

    s_elt           source elemement - instance of a type
    d_elt           destination element - instance of a type
    s_field_name    name of source field (or udf) to be copied 
    d_udf_name      name of destination udf name. If not specifyed
                    s_field_name will be used.

    The copy_udf() function takes a logfile as optional argument.
    If this is given the changes will be logged there.

    Written by Maya Brandi and Johannes Alnberg
    """
    def __init__(self, s_elt, d_elt, s_field_name, d_udf_name = None):
        if not d_udf_name:
            d_udf_name = s_field_name
        self.s_elt = s_elt
        self.s_field_name = s_field_name
        self.s_field = self._get_field(s_elt, s_field_name)
        self.d_elt = d_elt
        self.d_udf_name = d_udf_name
        self.old_dest_udf = self._get_field(d_elt, d_udf_name)

    def _current_time(self):
        return strftime("%Y-%m-%d %H:%M:%S", localtime())

    def _get_field(self, elt, field):
        if field in elt.udf:
            return elt.udf[field]
        elif udf_name in dir(elt):
            return elt.field
        else:
            return None

    def _set_udf(self, elt, udf_name, val):
        try:
            self.elt.udf[udf_name] = val
            self.elt.put()
        except (TypeError, HTTPError) as e:
            print >> sys.stderr, "Error while updating element: {0}".format(e)
            sys.exit(-1)

    def _log_before_change(self, changelog_f=None):
        if changelog_f:
            d = {'ct' : self._current_time(),
                 's_udf' : self.s_field_name,
                 'sn' : self.d_elt.name,
                 'si' : self.d_elt.id,
                 'su' : self.old_dest_udf,
                 'nv' : self.s_field}

            changelog_f.write(("{ct}: udf: {s_udf} on {sn} (id: {si}) from "
                               "{su} to {nv}.\n").format(**d))

        logging.info(("Copying from element with id: {0} to sample with "
                      " id: {1}").format(self.s_elt.id, self.d_elt.id))
         
    def _log_after_change(self):
        d = {'s_udf': self.s_field_name, 
             'd_udf': self.d_udf_name,
             'su': self.old_dest_udf,
             'nv': self.s_field, 
             'd_elt_type': self.d_elt._URI}

        logging.info("Updated {d_elt_type} udf: {d_udf}, from {su} to {nv}.".format(**d))
    
    def copy_udf(self, changelog_f = None):
        if self.s_field != self.old_dest_udf:
            self._log_before_change(changelog_f)
            self._set_udf(self.d_elt, self.d_udf_name, self.s_field)
            self._log_after_change()

def get_run_info(fc):
	fc_summary={}
	for iom in fc.input_output_maps:
		art = iom[0]['uri']
		lane = art.location[1].split(':')[0]
		if not fc_summary.has_key(lane):
     			fc_summary[lane]= dict(art.udf.items()) #"%.2f" % val ----round??
	return fc_summary







