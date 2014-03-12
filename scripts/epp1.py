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


def make_standards_list(result_file):
    standards_dict = {}
    standards_list = np.ones(8)
    for k,v in result_file.items():
        if set(['Sample','End RFU']).issubset(v) and v['Sample'].split()[0]=='Standard':
            standard = int(v['Sample'].split()[1])
            standards_dict[standard] = float(v['End RFU'])
    for k,v in standards_dict.items():
        standards_list[k-1] = v - standards_dict[1]
    return standards_list

def amount_in_standards(standard_volume, standard_dilution, assay_type):
    nuclear_acid_amount = np.ones(8)
    supp_conc_stds = {'RNA BR':[0,5,10,20,40,60,80,100],
                      'RNA':[0,5,10,20,40,60,80,100]}    
    for standard in range(8):
        nuclear_acid_amount[standard] = np.true_divide(supp_conc_stds[assay_type][standard]*standard_volume, standard_dilution)
    return nuclear_acid_amount

def linear_regression(X,Y):
    "Returns slope and intersect of linear regression on lists X and Y"
    A = np.array([ X, np.ones(len(X))])
    mod, resid = np.linalg.lstsq(A.T,Y)[:2]
    R2 = 1 - resid / (Y.size * Y.var())
    return R2, mod

def verify_standards(standards_file, udfs):
    X = make_standards_list(standards_file)
    Y = amount_in_standards(udfs['standard_volume'], 
                    udfs['standard_dilution'], udfs['assay_type'])
    R2, mod = linear_regression(X,Y)
    if R2 >= udfs['linearity_of_standards']:
        return mod, "R2 = {0}. Standards OK. Upload input file(s) for samples".format(R2) 
    else: 
        return mod, "R2 = {0}. Problem with standards! Redo measurement!".format(R2)

def calculate_concentration(mod, target_file, sample_volume, result_files):
    sample = target_file.samples[0].name
    fluor_int = []
    for f_name ,formated_file in result_files.items():
        if sample in formated_file:
            fluor_int.append(formated_file[sample]['End RFU'])
            target_file.udf[f_name] = formated_file[sample]['End RFU']  
    mean_fluor_int = np.mean(fluor_int)
    rel_fluor_int = mean_fluor_int - End_RFU_of_Standard_1
    conc = np.true_divide((slope * rel_fluor_int + intersect) , sample_volume)
    target_file.udf['Concentration'] = conc
    target_file.udf['Conc. Units'] = 'ng/ul'
    return target_file

def main(lims, pid, epp_logger):
    process = Process(lims,id = pid)
    udfs = {}
    file_handler = ReadResultFiles(process)
    standards_file = file_handler.shared_files['Standards File (.txt)']
    standards_file_formated, warn = file_handler.format_file(standards_file,header_row = 26)
    for f_name in ['Quant-iT Result File 1','Quant-iT Result File 2']:
        if file_handler.shared_files.has_key(f_name):
            quantit_result_file = file_handler.shared_files[f_name]
            result_files[f_name] = file_handler.format_file(quantit_result_file, first_header = 'Sample', root_key_col = 1)
    target_files = process.result_files()
    result_files = {}
    
    try:
        udfs['assay_type'] = process.udf['Assay type']
        udfs['standard_volume'] = process.udf['Standard volume']
        udfs['linearity_of_standards'] = process.udf['Linearity of standards']
        udfs['standard_dilution'] = process.udf['Standard dilution']    
        udfs['sample_volume'] = process.udf['Sample volume']
    except:
        abstract = """process udfs missing. Please make sure 'Assay type', 
                    'Standard volume', 'Linearity of standards', 'Sample volume'
                     and 'Standard dilution' are well defined."""
    if udfs:
        mod, abstract = verify_standards(standards_file_formated, udfs)
        for target_file in target_files:
            target_file = calculate_concentration(mod, target_file, udfs['sample_volume'], result_files)
            try:
                target_file.put()
            except (TypeError, HTTPError) as e:
                logging.warning("Error while updating element: {0}".format(e))


    logging.info(abstract)
    print >> sys.stderr, abstract

if __name__ == "__main__":
    parser = ArgumentParser(description=DESC)
    parser.add_argument('--pid', default = None , dest = 'pid',
                        help='Lims id for current Process')
    parser.add_argument('--log', dest = 'log',
                        help=('File name for standard log file, '
                              'for runtime information and problems.'))

    args = parser.parse_args()

    lims = Lims(BASEURI,USERNAME,PASSWORD)
    lims.check_version()

    with EppLogger(log_file=args.log, lims=lims, prepend=True) as epp_logger:
        main(lims, args.pid, epp_logger)

