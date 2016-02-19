"""
This file together with bcl_thresholds.py performs the bclconversion step of LIMS workflow.
In common tongue, it:
 
Fetches some info from the workflow process
Assigns a few thresholds to the process (workflow step)
Reformats laneBarcode.html for usage of other applications
Assigns some info from laneBarcode.html to individual samples in the process
Flags samples as QC PASS/FAIL based on thresholds

##As of implementation preproc2 has hiseq examples & Preproc 1 has hiseqX
##lanebc file is stored in Demultiplexing_0 on nosync on /srv/illumina

Written by Isak Sylvin; isak.sylvin@scilifelab.se"""

from genologics.lims import Lims
from genologics.config import BASEURI, USERNAME, PASSWORD
from genologics.entities import Process
from genologics.epp import EppLogger
import flowcell_parser.classes as classes
from bcl_thresholds import Thresholds
from datetime import datetime
from time import time

import os 
import click
import csv
import pdb
import sys
import logging

timestamp = datetime.fromtimestamp(time()).strftime('%Y-%m-%d_%H:%M')

"""Fetches overarching workflow info"""
def manipulate_workflow(demux_process):
    try:
        demux_container = demux_process.all_inputs()[0].location[0].name    
    except:
        sys.exit("Container name not found")
        
    workflow_types = {'MiSeq Run (MiSeq) 4.0':'Reagent Cartridge ID', 'Illumina Sequencing (Illumina SBS) 4.0':'Flow Cell ID',
              'Illumina Sequencing (HiSeq X) 1.0':'Flow Cell ID'}
    for k,v in workflow_types.items():
        #Workflow is null if it doesn't exist
        workflow = lims.get_processes(udf = {v : demux_container}, type = k)
        #If workflow key exists
        if(workflow):
            #Copies LIMS workflow content
            proc_stats = dict(workflow[0].udf.items())
            if 'MiSeq Run (MiSeq) 4.0' in k:
                proc_stats['Run type'] ='MiSeq'
                proc_stats['Data type'] = 'miseq'
            elif 'Illumina Sequencing (Illumina SBS) 4.0' in k:
                proc_stats['Run type'] = workflow[0].udf['Flow Cell Version']
                proc_stats['Data type'] = 'hiseq'
            elif 'Illumina Sequencing (HiSeq X) 1.0' in k:
                proc_stats['Run type'] ='HiSeqX10'
                proc_stats['Data type'] = 'HiSeqX'
            else:
                sys.exit("Unhandled prior workflow step (run type)")
            logging.info("Run type set to " + proc_stats['Run type'])
            break
        
    proc_stats['paired'] = False
    if 'Read 2 Cycles ' in proc_stats:
        proc_stats['paired'] = True
    logging.info("Paired libraries: " + str(proc_stats['paired']))  
    
    return proc_stats

"""Sets run thresholds"""
#Chemistry for miseq and x10 needs to be expanded
def manipulate_process(demux_process, proc_stats):      
    thresholds = Thresholds('HiSeq', proc_stats['Run type'], proc_stats['paired'])
    Q30_thres = thresholds.Q30
    exp_lane_clust = thresholds.exp_lane_clust
    
    if not 'Threshold for % bases >= Q30' in demux_process.udf:
        try:
            demux_process.udf['Threshold for % bases >= Q30'] = Q30_thres
        except:
            sys.exit("Udf improperly formatted. Unable to set Q30 threshold")
    #Would prefer 'Expected reads per lane' put this is easier
    if not 'Threshold for # Reads' in demux_process.udf:
        try:
            demux_process.udf['Threshold for # Reads'] = exp_lane_clust
        except:
            sys.exit("Udf improperly formatted. Unable to set # Reads threshold")

      
    logging.info("Q30 threshold set to " + str(Q30_thres))
    logging.info("Minimum clusters per lane set to " + str(exp_lane_clust))
    
    try:
        demux_process.put()
    except:
        sys.exit("Failed to apply process thresholds to LIMS")
    
"""Sets artifact = samples values """
def set_sample_values(demux_process, parser_struct, proc_stats):
    for pool in demux_process.all_inputs():
        try:
            outarts_per_lane = demux_process.outputs_per_input(pool.id, ResultFile = True)
        except:
            sys.exit('Unable to fetch artifacts of process')
        if proc_stats['Run type'] == 'Miseq':
            lane_no = '1'
        else:
            try:
                lane_no = pool.location[1][0]
            except:
                sys.exit('Unable to determine lane number. Incorrect location variable in process.')
        logging.info("Lane number set to " + lane_no)
        exp_smp_per_lne = round(demux_process.udf['Threshold for # Reads']/float(len(outarts_per_lane)), 0)
        logging.info('Expected sample clusters for this lane: ' + str(exp_smp_per_lne))
        for target_file in outarts_per_lane:
            try:
                current_name = target_file.samples[0].name
            except:
                sys.exit('Unable to determine sample name. Incorrect sample variable in process.')
            for entry in parser_struct:
                if lane_no == entry['Lane']:
                    sample = entry['Sample']
                    if sample == current_name:
                        try:
                            target_file.udf['%PF'] = float(entry['% PFClusters'])
                            target_file.udf['% One Mismatch Reads (Index)'] = float(entry['% One mismatchbarcode'])
                            target_file.udf['% of Raw Clusters Per Lane'] = float(entry['% of thelane'])
                            target_file.udf['Ave Q Score'] = float(entry['Mean QualityScore'])
                            target_file.udf['% Perfect Index Read'] = float(entry['% Perfectbarcode'])
                            target_file.udf['Yield PF (Gb)'] = float(entry['Yield (Mbases)'].replace(',',''))/1000
                            target_file.udf['% Bases >=Q30'] = float(entry['% >= Q30bases'])
                            target_file.udf['# Reads'] = int(entry['PF Clusters'].replace(',',''))
                            if proc_stats['paired']:
                                target_file.udf['# Read Pairs'] = float(entry['PF Clusters'].replace(',',''))/2
                            else:
                                target_file.udf['# Read Pairs'] = int(entry['PF Clusters'].replace(',',''))
                        except:
                            sys.exit("Unable to set artifact values.")
                        logging.info('Added the following set of values to artifact:')
                        logging.info(str(target_file.udf['%PF']) + ' %PF')
                        logging.info(str(target_file.udf['% One Mismatch Reads (Index)']) + ' % One Mismatch Reads (Index)')
                        logging.info(str(target_file.udf['% of Raw Clusters Per Lane']) + ' % of Raw Clusters Per Lane')
                        logging.info(str(target_file.udf['Ave Q Score']) + ' Ave Q Score')
                        logging.info(str(target_file.udf['% Perfect Index Read']) + ' % Perfect Index Read')
                        logging.info(str(target_file.udf['Yield PF (Gb)']) + ' Yield (Mbases)')
                        logging.info(str(target_file.udf['% Bases >=Q30']) + ' % Bases >=Q30')
                        logging.info(str(target_file.udf['# Reads']) + ' # Reads')
                        logging.info(str(target_file.udf['# Read Pairs']) + ' # Reads Pairs')
                        
                        try:
                            if 'Clusters' in entry:
                                reads = entry['Clusters']
                            else: 
                                reads = entry['PF Clusters']
                            reads = int(reads.replace(',',''))
                            if ( demux_process.udf['Threshold for % bases >= Q30'] > float(entry['% >= Q30bases']) and 
                            exp_smp_per_lne > reads ):
                                target_file.udf['Include reads'] = 'YES'
                                target_file.qc_flag = 'PASSED'           
                            else:
                                target_file.udf['Include reads'] = 'NO'
                                target_file.qc_flag = 'FAILED'
                            logging.info('Sample QC status set to ' + target_file.qc_flag )
                        except:
                            sys.exit("Unable to set QC status for sample")
            try:
                target_file.put()
            except:
                sys.exit("Failed to apply artifact data to LIMS")
    

"""Creates demux_{FCID}_{time}.csv and attaches it to process"""
#Handles undetermined quite badly, might be worth revising
    #change TEMPORARY LINE once done
    #current pid is 24-142862
def write_demuxfile(proc_stats):
    prefix = '/srv/illumina/'+ proc_stats['Data type'] + '_data/nosync/'
    try:
        appendix = proc_stats['Run ID'] + '/Demultiplexing/Reports/html/' + proc_stats['Flow Cell ID'] + '/all/all/all/laneBarcode.html'
    except:
        sys.exit("Unable to set demux filename. Udf does not contain keys for run id and/or flowcell id.")
    lanebc_path = prefix + appendix
    #TEMPORARY LINE
    lanebc_path = '/Users/isaksylvin/SciLifeLab/preprocExampleData/24-142862/laneBarcode.html'
    try:
        laneBC = classes.LaneBarcodeParser(lanebc_path)
    except:
        sys.exit("Unable to fetch laneBarcode.html from " + lanebc_path)
    fname = 'demuxstats' + '_' + proc_stats['Flow Cell ID'] + '_' + timestamp + '.csv'
    
    with open(fname, 'w') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(['Project', 'Sample ID', 'Lane', '# Reads', 'Index','Index name', '% of >= Q30 Bases (PF)'])
        for entry in laneBC.sample_data:
            if 'Clusters' in entry:
                reads = entry['Clusters']
            else: 
                reads = entry['PF Clusters']
            reads = int(reads.replace(',',''))
            index_name = ""
            try:
                writer.writerow([entry['Project'],entry['Sample'],entry['Lane'],reads,entry['Barcode sequence'],index_name,entry['% >= Q30bases']])
            except:
                sys.exit("Flowcell parser is unable to fetch all necessary fields for demux file.")
    return laneBC.sample_data

def converter(demux_process, epp_logger):
    #Fetches workflow info
    proc_stats = manipulate_workflow(demux_process)
    #Sets up the process values
    manipulate_process(demux_process, proc_stats)
    #Create the attached csv file
    parser_struct = write_demuxfile(proc_stats)
    #Alters artifacts
    set_sample_values(demux_process, parser_struct, proc_stats)

@click.command()
@click.option('--project_lims_id', required=True,help='REQUIRED: Lims ID of project. Example:24-92373')
@click.option('--rt_log', default='runtime_'+ timestamp + '.log', 
              help='File name to log runtime information. Default:runtime_TIME.log') 
def main(project_lims_id, rt_log):
    demux_process = Process(lims,id = project_lims_id)
    #Sets up proper logging
    with EppLogger(log_file=rt_log, lims=lims, prepend=True) as epp_logger:
        converter(demux_process, epp_logger)
           
if __name__ == '__main__':
    lims = Lims(BASEURI, USERNAME, PASSWORD)
    lims.check_version()
    main()
