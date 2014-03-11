#!/usr/bin/env python
DESC = """EPP script to copy user defined field from any process to associated 
project/projects in Clarity LIMS. If the specifyed process handles many artifacts 
associated to different projects, all these projects will get the specifyed udf.
 
Can be executed in the background or triggered by a user pressing a "blue button".

The script can output two different logs, where the status_changelog 
contains notes with the technician, the date and changed status for each 
copied status. The regular log file contains regular execution information.

Written by Maya Brandi 
"""
import os
import sys
import logging
import numpy as np

from argparse import ArgumentParser
from requests import HTTPError
from genologics.lims import Lims
from genologics.config import BASEURI,USERNAME,PASSWORD
from genologics.entities import Process
from genologics.epp import EppLogger
from genologics.epp import ReadResultFiles
lims = Lims(BASEURI,USERNAME,PASSWORD)

def make_standards_dict(quantit_result_file):
    ... 'End RFU'
    standards_dict = {}
    standard - 'Standard 1'....
    return standards_dict

def make_nuclear_acid_amount_in_standards(standard_volume, standard_dilution, assay_type):
    nuclear_acid_amount = {}
    supp_conc_stds = {'BR conc (ng/uL)':[0,5,10,20,40,60,80,100],
                      'HS conc (ng/uL)':[0,5,10,20,40,60,80,100]}    
    for standard in range(8):
        nuclear_acid_amount[standard] = supp_conc_stds[assay_type][standard] * standard_volume / standard_dilution
    return nuclear_acid_amount

def linear_regression(X,Y):
    "Returns slope and intersect of linear regression on lists X and Y"
    A = array([ X, ones(len(X))])
    Y = [19, 20, 20.5, 21.5, 22, 23, 23, 25.5, 24]
    W = linalg.lstsq(A.T,Y)[0]
    return W

def main(lims, pid, epp_logger):
    process = Process(lims,id = pid)

    file_handler = ReadResultFiles(process)
    quantit_result_file = file_handler.shared_files['Standards File (.txt)']
    quantit_result_file, warn = file_handler.format_file(quantit_result_file)

    R2 = Pearson correlation coefficient
    assay_type = process.udf.items()['Assay Type']
    standard_volume = process.udf.items()['Standard volume']
    linearity_of_standards = process.udf.items()['Linearity of standards']
    standard_dilution = process.udf.items()['Standard dilution']    
    
    X = make_standards_dict(quantit_result_file)
    Y = make_nuclear_acid_amount_in_standards(standard_volume, standard_dilution, assay_type)
    slope, intersect = linear_regression(X,Y)

    if R2 >= slope:
        abstract = "Standards OK. Upload input file(s) for samples" 
    else: 
        abstract = "Problem with standards! Redo measurement!"

    print >> sys.stderr, abstract

if __name__ == "__main__":
    parser = ArgumentParser(description=DESC)
    parser.add_argument('--pid', default = '24-38458', dest = 'pid',
                        help='Lims id for current Process')
    parser.add_argument('--log', dest = 'log',
                        help=('File name for standard log file, '
                              'for runtime information and problems.'))

    args = parser.parse_args()

    lims = Lims(BASEURI,USERNAME,PASSWORD)
    lims.check_version()

    with EppLogger(log_file=args.log, lims=lims, prepend=True) as epp_logger:
        main(lims, args.pid, epp_logger)

