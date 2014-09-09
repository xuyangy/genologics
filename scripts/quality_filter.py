#!/usr/bin/env python
DESC = """EPP script for Quant-iT measurements to calculate concentrations and 
load input artifact-udfs and output file-udfs of the process with concentration 
values and fluorescence intensity.

Reads from:
    --Lims fields--
    "Assay type"                process udf 
    "Standard volume"           process udf
    "Standard dilution"         process udf
    "Linearity of standards"    process udf
    "Sample volume"             process udf

    --files--
    "Standards File (.txt)"     "shared result file" uploaded by user.   
    "Quant-iT Result File 1"    "shared result file" uploaded by user.
    "Quant-iT Result File 2"    "shared result file" uploaded by user. (optional)

Writes to:
    --Lims fields--
    "Fluorescence intensity 1"  udf of input analytes to the process
    "Fluorescence intensity 2"  udf of input analytes to the  process
    "Concentration"             udf of process artifacts (result file)
    "Conc. Units"               udf of process artifacts (result file)

Logging:
    The script outputs a regular log file with regular execution information.

Performance:
    1)  Makes a linear regression analysis on the End RFU standards read from 
    "Standards File (.txt)" --> slope, intersect and R2 (Pearson correlation 
    coefficient)

    2)  If R2 is less than "Linearity of standards", standards are not ok and 
    the user is warned "Problem with standards! Redo measurement!". 

    3)  If R2 is greater than "Linearity of standards", concentration values are
    calculated based on the linear regression parameters, copied to the 
    "Concentration"-udf on the output artifacts (one result file per sample). 
    The "Conc. Units"-udf on the same artifacts are set to "ng/ul".

    4)  "End RFU" values from "Quant-iT Result File 1" are copied to the udf
    "Fluorescence intensity 1" of the input analyte to the process, and 
    "End RFU" values from "Quant-iT Result File 2" are copied to the udf 
    "Fluorescence intensity 2". 

Written by Maya Brandi 
"""

import os
import sys
import logging
import numpy as np

from argparse import ArgumentParser
from genologics.lims import Lims
from genologics.config import BASEURI,USERNAME,PASSWORD
from genologics.entities import Process
from genologics.epp import EppLogger
from genologics.epp import set_field
from genologics.epp import ReadResultFiles

class QualityFilter():
    def __init__(self, process):
        self.process = process
        self.result_files = process.result_files()
        self.QF_from_file = {}
        self.missing_samps = []
        self.abstract = []
        self.nr_updat_samps = 0

    def get_and_set_yield_and_Q30(self):
        file_handler = ReadResultFiles(self.process)
        source_file = file_handler.shared_files['Quality Filter']
        print '*******'
        print source_file
        target_files = dict((r.samples[0].name, r) for r in self.result_files)
        self.QF_from_file = file_handler.format_file(source_file, 
                               name = 'Quality Filter', first_header = 'Sample')
        for samp_name, target_file in target_files.items():
            self._set_udfs(samp_name, target_file)
            self.nr_updat_samps += 1
        self._logging()

    def _set_udfs(self, samp_name, target_file):
        if samp_name in self.QF_from_file.keys():
            s_inf = self.QF_from_file[samp_name]
            target_file.udf['# Reads'] = int(s_inf['# Reads'])
            target_file.udf['% Bases >=Q30'] = float(s_inf['% Bases >=Q30'])
        else:
            self.missing_samps.append(samp_name)
        set_field(target_file)

    def _logging(self):
        self.abstract.append("Yield and Q30 uploaded for {0} samples.".format(
                                                           self.nr_updat_samps))
        if self.missing_samps:
            self.abstract.append("The following samples are missing in Quality "
            "Filter file: {0}.".format(', '.join(self.missing_samps)))
        print >> sys.stderr, ' '.join(self.abstract)

def main(lims, pid, epp_logger):
    process = Process(lims,id = pid)
    QF = QualityFilter(process)
    QF.get_and_set_yield_and_Q30()
    

if __name__ == "__main__":
    parser = ArgumentParser(description=DESC)
    parser.add_argument('--pid', default = None , dest = 'pid',
                        help='Lims id for current Process')
    parser.add_argument('--log', dest = 'log',
                        help=('File name for standard log file, '
                              'for runtime information and problems.'))

    args = parser.parse_args()
    lims = Lims(BASEURI, USERNAME, PASSWORD)
    lims.check_version()

    with EppLogger(log_file=args.log, lims=lims, prepend=True) as epp_logger:
        main(lims, args.pid, epp_logger)
