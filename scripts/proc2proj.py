#!/usr/bin/env python
DESC = """EPP script to copy user defined field from process 
level to project level in Clarity LIMS. Can be executed in the 
background or triggered by a user pressing a "blue button".

The script can output two different logs, where the status_changelog 
contains notes with the technician, the date and changed status for each 
copied status. The regular log file contains regular execution information. 

Error handling:
If the field given is blank or not defined for the proocess,
the script will log this, and not perform any changes.
""" 

from argparse import ArgumentParser

from genologics.lims import Lims
from genologics.config import BASEURI,USERNAME,PASSWORD

from genologics.entities import Process, Artifact
from genologics.epp import EppLogger

import logging
import sys

from shutil import copy
import os

from time import strftime, localtime
from requests import HTTPError

from genologics.lims_utils import CopyField

def main(lims, argsi, epp_logger):
    s_elt = Process(lims,id = args.pid)
    d_elt = s_elt.all_inputs()[0].samples[0].project
        
    if args.status_changelog:
        dir = os.getcwd()
        destination = os.path.join(dir, args.status_changelog)
        if not os.path.isfile(destination):
            epp_logger.prepend_old_log(args.status_changelog)

    with open(args.status_changelog, 'a') as changelog_f:
        if args.source_udf in s_elt.udf:
            copy_sesion = CopyField(s_elt, d_elt, args.source_udf, args.dest_udf)
            copy_sesion.copy_udf(changelog_f)
        else:
            logging.warning(("Udf: {1} in Process {0} is undefined/blank, exiting").format(s_elt.name, args.source_udf))

if __name__ == "__main__":
    parser = ArgumentParser(description=DESC)
    parser.add_argument('--pid',
                        help='Lims id for current Process')
    parser.add_argument('--log',
                        help=('File name for standard log file, '
                              ' for runtime information and problems.'))
    parser.add_argument('-s', '--source_udf', type=str, default=None,
                        help=('Name of the source user defined field that will'
                              'be copied.'))
    parser.add_argument('-d', '--dest_udf', type=str, default=None,
                        help=('Name of the destination user defined field that will'
                              'be written to. This argument is optional, if left empty'
                              'the source_udf argument is used instead.'))
    parser.add_argument('-c', '--status_changelog',
                        help=('File name for status changelog file, '
                              ' for concise information on who, what and '
                              ' when for status change events. '
                              'Prepends the old changelog file by default.'))

    args = parser.parse_args()

    lims = Lims(BASEURI,USERNAME,PASSWORD)
    lims.check_version()

    with EppLogger(args.log, lims=lims, prepend=True) as epp_logger:
        main(lims, args, epp_logger)
