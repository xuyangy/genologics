#!/usr/bin/env python

DESC = """EPP script to copy 'concentration' and 'concentration unit' for each 
sample sample in the 'Qubit Result File' to the 'Concentration' and 'Conc. Units' 
fields of the output analytes of the process.

Warnings are generated to the user and stored in regular log file wich allso 
contains regular execution information in the folowing cases:

1) missing row names (samples) in file
2) duplicated row names (samples)
3) missing value (concentrations) 
4) values found but for some reason are not successfully copied:
 
Can be executed in the background or triggered by a user pressing a "blue button".

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
from genologics.epp import set_field
lims = Lims(BASEURI,USERNAME,PASSWORD)

def main(lims, pid, epp_logger):
    process = Process(lims,id = pid)
    target_files = process.result_files()
    file_handler = ReadResultFiles(process)
    files = file_handler.shared_files['Qubit Result File']
    qubit_result_file = file_handler.format_file(files, 
                                                 name = 'Qubit Result File',
                                                 first_header = 'Sample')
    missing_samples = []
    bad_formated = []
    abstract = []
    udfs = dict(process.udfs.items())
    if udfs.has_key("Minimum required concentration (ng/ul)"):
        min_conc = udfs["Minimum required concentration (ng/ul)"]
    else:
        min_conc = None
        abstract.append("Set 'Minimum required concentration (ng/ul)' for receving qc-flaggs")

    for target_file in target_files:
        sample = target_file.samples[0].name
        if qubit_result_file.has_key(sample):
            sample_mesurements = qubit_result_file[sample]
            if "Sample Concentration" in sample_mesurements.keys():
                conc, unit = sample_mesurements["Sample Concentration"]
                if conc == 'Out Of Range':
                    target_file.qc_flag = "FAILED"
                else:
                    try:
                        conc = float(conc)
                        if min_conc:
                            if conc < min_conc:
                                target_file.qc_flag = "FAILED"
                                self.low_conc +=1
                            else:
                                target_file.qc_flag = "PASSED"
                        if unit == 'ng/mL':
                            conc = np.true_divide(conc, 1000)
                        target_file.udf['Concentration'] = conc
                        target_file.udf['Conc. Units'] = 'ng/ul'
                    except:
                        bad_formated.append(sample)
                set_field(target_file)
        else:
            missing_samples.append(sample)

    if missing_samples:
        missing_samples = ', '.join(missing_samples)
        abstract.append('The folowing samples are missing in Qubit Result File: {0}'.format(missing_samples))
    if bad_formated:
        bad_formated = ', '.join(bad_formated)
        abstract.append('The folowing samples have badly formated info in Qubit Result File: {0}'.format(bad_formated))

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

