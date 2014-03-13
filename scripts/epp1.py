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

class QunatiT():
    def __init__(self, process):
        self.file_handler = ReadResultFiles(process)
        self.udfs = dict(process.udf.items())
        self.abstract = []
        self.missing_udfs = []
        self.standards = self._make_standards_list()
        print self.standards
        self.mod, self.R2 = self._verify_standards()

    def _formated_result_files_dict(self):
        result_files = {}
        file_names = {'Quant-iT Result File 1':'Fluorescence intensity 1',
                    'Quant-iT Result File 2':'Fluorescence intensity 2'}
        for f_name, udf_name in file_names.items():
            if self.file_handler.shared_files.has_key(f_name):
                result_file = self.file_handler.shared_files[f_name]
                result_files[udf_name], warn = self.file_handler.format_file(result_file,
                                                        first_header = 'Sample', root_key_col = 1)
                if warn:
                    self.abstract.append(' '.join([warn, f_name]))
        return result_files
 
    def _make_standards_list(self):
        standards_file = self.file_handler.shared_files['Standards File (.txt)']
        standards_file_formated, warn = self.file_handler.format_file(standards_file, header_row = 26)
        standards_dict = {}
        for k,v in standards_file_formated.items():
            if set(['Sample','End RFU']).issubset(v) and v['Sample'].split()[0]=='Standard':
                standard = int(v['Sample'].split()[1])
                standards_dict[standard] = float(v['End RFU'])
        return standards_dict

    def _amount_in_standards(self):
        nuclear_acid_amount = np.ones(8)
        supp_conc_stds = {'RNA BR':[0,5,10,20,40,60,80,100],
                          'RNA':[0,5,10,20,40,60,80,100]}    
        if set(['Standard volume','Assay type','Standard dilution']).issubset(self.udfs.keys()):
            for standard in range(8):
                nuclear_acid_amount[standard] = np.true_divide(supp_conc_stds[self.udfs['Assay type']][standard] * 
                    self.udfs['Standard volume'], self.udfs['Standard dilution'])
            return nuclear_acid_amount
        else:
            self.missing_udfs += ['Standard volume','Assay type','Standard dilution']
            return None

    def _linear_regression(self, X,Y):
        A = np.array([ X, np.ones(len(X))])
        mod, resid = np.linalg.lstsq(A.T,Y)[:2]
        R2 = 1 - resid / (Y.size * Y.var())
        return R2, mod

    def _verify_standards(self):
        relative_standards = np.ones(8)
        for k,v in self.standards.items(): 
            relative_standards[k-1] = v - self.standards[1]
        amount_in_standards = self._amount_in_standards()
        R2, mod = self._linear_regression(relative_standards, amount_in_standards)
        return mod, R2

    def calculate_concentration(self, target_file, target_analyte):
        result_files = self._formated_result_files_dict()
        sample = target_file.samples[0].name
        slope = self.mod[0]
        intersect = self.mod[1]
        fluor_int = []
        for udf_name ,formated_file in result_files.items():
            if sample in formated_file.keys():
                fluor_int.append(int(formated_file[sample]['End RFU']))
                target_analyte.udf[udf_name] = int(formated_file[sample]['End RFU']) 
            else:
                self.abstract.append("Sample {0} is not represented in Result File for filed {1}.".format(sample, udf_name))
        mean_fluor_int = np.mean(fluor_int)
        rel_fluor_int = mean_fluor_int - self.standards[1]
        if 'Sample volume' in self.udfs.keys():
            conc = np.true_divide((slope * rel_fluor_int + intersect) , self.udfs['Sample volume'])
            target_file.udf['Concentration'] = conc
            target_file.udf['Conc. Units'] = 'ng/ul'
        else:
            self.missing_udfs.append('Sample volume')
        return target_file, target_analyte


def main(lims, pid, epp_logger):
    process = Process(lims,id = pid)
    qunatit = QunatiT(process)
    target_files = dict((r.samples[0].name, r) for r in process.result_files())
    target_analytes = dict((a.name, a) for a in process.analytes()[0])

    if 'Linearity of standards' in qunatit.udfs.keys():
        if qunatit.R2 >= qunatit.udfs['Linearity of standards']:
            qunatit.abstract.append("R2 = {0}. Standards OK.".format(qunatit.R2))
            for sample, target_file in target_files.items():
                target_analyte = target_analytes[sample]
                target_file, target_analyte = qunatit.calculate_concentration(target_file, target_analyte)
                try:
                    target_file.put()
                except (TypeError, HTTPError) as e:
                    logging.warning("Error while updating element: {0}".format(e))
                try:
                    target_analyte.put()
                except (TypeError, HTTPError) as e:
                    logging.warning("Error while updating element: {0}".format(e))
        else:
            qunatit.abstract.append("R2 = {0}. Problem with standards! Redo measurement!".format(qunatit.R2))
    else:
        qunatit.abstract.append("Kould not calculate concentration. Please set 'Linearity of standards'.")

    if qunatit.missing_udfs:
        qunatit.abstract.append("Are all of the folowing udfs set? : {0}".format(', '.join(qunatit.missing_udfs)))
    
    abstract = ' '.join(qunatit.abstract)

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

