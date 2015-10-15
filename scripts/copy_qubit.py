#!/usr/bin/env python
# -*- coding: utf-8 -*-


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

Written by Maya Brandi and Denis Moreno
"""

import os
import sys
import logging
import numpy as np
import codecs

from argparse import ArgumentParser
from requests import HTTPError
from genologics.lims import Lims
from genologics.config import BASEURI,USERNAME,PASSWORD
from genologics.entities import Process
from genologics.epp import EppLogger
from genologics.epp import ReadResultFiles
from genologics.epp import set_field

import csv

def get_qbit_file(process):
        outs = process.all_outputs()
        for outart in outs:
            #get the right output artifact
            if outart.type == 'ResultFile' and outart.name == 'Qubit Result File':
                #get the associated file
                csvfile = outart.files[0]
                #content location is a ugly sftp uri
                file_path = csvfile.content_location.split('scilifelab.se')[1]
                return file_path
        return None

def get_data(file_path, log):
    read=False
    data={}
    utflines=[]
    with codecs.open(file_path ,'rb', 'iso-8859-1') as f:
        #utf-8 translation, thanks qubit. 
        for l in f:
            utflines.append(l.encode('utf-8'))

        pf = csv.reader(utflines)
        #New Qubit
        #defaults
        sample_index=2
        conc_index=6
        conc_unit=7
        for row in pf:
            if 'Test Name' in row:
                #this is the header row
                sample_index=row.index('Test Name')
                conc_index=row.index('Original sample conc.')
                unit_index=conc_index+1
                read=True
            elif(read and row[sample_index]):
                #this is every other row
                if row[sample_index] in data:
                    #Sample is duplicated, drop the key
                    log.append("sample {0} has two rows in the Qubit CSV file. Please check the file manually.".format(row[sample_index]))
                    del data[row[sample_index]]

                else:
                    #normal procedure
                    data[row[sample_index]]={}
                    data[row[sample_index]]['concentration']=row[conc_index]
                    data[row[sample_index]]['unit']=row[unit_index]
            elif (not read  and 'Sample' in row):
                sample_index=row.index('Sample')
                conc_index=row.index('Sample Concentration')
                unit_index=conc_index+1
                read=True
    return data

def convert_to_ng_ul(conc, unit):
    factor=float(1.0)#I really want a float
    units=unit.split('/')
    if units[0] == 'µg' or units[0] == 'ug':
        factor*=1000
    elif units[0] == 'mg':
        factor*=1000000
    if units[1] == 'mL':
        factor/=1000
    if units[1] == 'nL':
        factor*=1000

    return conc*factor


def get_qbit_csv_data(process):
    #samples missing from the qubit csv file
    missing_samples = 0
    low_conc = 0
    bad_format = 0
    #strings returned to the EPP user
    log = []

    #get file path by parsing lims artifacts
    file_path=get_qbit_file(process)
    #parse the qubit file and get the interesting data out
    data=get_data(file_path, log)

    if "Minimum required concentration (ng/ul)" in process.udf:
        min_conc=process.udf['Minimum required concentration (ng/ul)']
    else:
        min_conc=None
        log.append("Set 'Minimum required concentration (ng/ul)' to get qc-flags based on this threshold!")

    for target_file in process.result_files():
        conc=None
        new_conc=None
        file_sample=target_file.samples[0].name
        if file_sample in data:
            try:
                conc=float(data[file_sample]['concentration'])
            except ValueError:
                #concentration is not a float
                target_file.qc_flag = "FAILED"
                if data[file_sample]['concentration'] != 'Out of range':
                    #Out of range is a valid value, the others are not.
                    bad_format+=1

            else:
                new_conc=convert_to_ng_ul(conc, data[file_sample]['unit'])
                if new_conc is not None : 
                    target_file.udf['Concentration'] = new_conc
                    target_file.udf['Conc. Units'] = 'ng/ul'
                    if new_conc < min_conc:
                        target_file.qc_flag = "FAILED"
                        low_conc +=1
                    else:
                        target_file.qc_flag = "PASSED"

            #actually set the data
            target_file.put()
            set_field(target_file)
        else:
            missing_samples += 1
    if low_conc:
        log.append('{0}/{1} samples have low concentration.'.format(low_conc, len(process.result_files())))
    if missing_samples:
        log.append('{0}/{1} samples are missing in the Qubit Result File.'.format(missing_samples, len(process.result_files())))
    if bad_format:
        log.append('There are {0} badly formatted samples in Qubit Result File. Please fix these to get proper results.'.format(bad_format))

    print(''.join(log), file=sys.stderr)

def main(lims, pid, epp_logger):

    process = Process(lims,id = pid)
    get_qbit_csv_data(process)

def old_main(lims, pid, epp_logger):
    process = Process(lims,id = pid)
    sample_names = [a.name for a in process.analytes()[0]]
    target_files = process.result_files()
    file_handler = ReadResultFiles(process)
    files = file_handler.shared_files['Qubit Result File']
    qubit_result_file = file_handler.format_file(files, 
                                                 name = 'Qubit Result File',
                                                 first_header = ['Test','Sample'],
                                                 find_keys = sample_names)
    missing_samples = 0
    low_conc = 0
    bad_formated = 0
    abstract = []
    udfs = dict(list(process.udf.items()))
    if "Minimum required concentration (ng/ul)" in udfs:
        min_conc = udfs["Minimum required concentration (ng/ul)"]
    else:
        min_conc = None
        abstract.append("Set 'Minimum required concentration (ng/ul)' to get qc-flaggs based on this treshold!")
    for target_file in target_files:
        sample = target_file.samples[0].name
        if sample in qubit_result_file:
            sample_mesurements = qubit_result_file[sample]
            if "Sample Concentration" in list(sample_mesurements.keys()):
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

