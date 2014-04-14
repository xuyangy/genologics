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
    sample_names = map(lambda a: a.name, process.analytes()[0])
    target_files = process.result_files()
    file_handler = ReadResultFiles(process)
    files = file_handler.shared_files['Qubit Result File']
    qubit_result_file = file_handler.format_file(files, 
                                                 name = 'Qubit Result File',
                                                 first_header = 'Sample',
                                                 find_keys = sample_names)
    missing_samples = 0
    low_conc = 0
    bad_formated = 0
    abstract = []
    udfs = dict(process.udf.items())
    if udfs.has_key("Minimum required concentration (ng/ul)"):
        min_conc = udfs["Minimum required concentration (ng/ul)"]
    else:
        min_conc = None
        abstract.append("Set 'Minimum required concentration (ng/ul)' to get qc-flaggs based on this treshold!")
    for target_file in target_files:
        sample = target_file.samples[0].name
        if qubit_result_file.has_key(sample):
            sample_mesurements = qubit_result_file[sample]
            if "Sample Concentration" in sample_mesurements.keys():
                conc, unit = sample_mesurements["Sample Concentration"]
                if conc == 'Out Of Range':
                    target_file.qc_flag = "FAILED"
                elif conc.replace('.','').isdigit():
                    conc = float(conc)
                    if unit == 'ng/mL':
                        conc = np.true_divide(conc, 1000)
                    if min_conc:
                        if conc < min_conc:
                            target_file.qc_flag = "FAILED"
                            low_conc +=1
                        else:
                            target_file.qc_flag = "PASSED"
                    target_file.udf['Concentration'] = conc
                    target_file.udf['Conc. Units'] = 'ng/ul'
                else:
                    bad_formated += 1
                set_field(target_file)
        else:
            missing_samples += 1

    if low_conc:
        abstract.append('{0}/{1} samples have low concentration.'.format(low_conc, len(target_files)))
    if missing_samples:
        abstract.append('{0}/{1} samples are missing in Qubit Result File.'.format(missing_samples, len(target_files)))
    if bad_formated:
        abstract.append('There are {0} badly formated samples in Qubit Result File. Please fix these to get proper results.'.format(bad_formated))

    print >> sys.stderr, ' '.join(abstract)

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

