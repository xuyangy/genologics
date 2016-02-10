"""Written by Isak Sylvin; isak.sylvin@scilifelab.se"""

from genologics.lims import Lims
from genologics.config import BASEURI, USERNAME, PASSWORD
from genologics.entities import Process
import flowcell_parser.classes as classes
from datetime import datetime

import os 
import click
import csv
import numpy
import pdb

def decide_thresholds(run_type, read_length):
    if run_type == 'MiSeq':
        if read_length < 101:
            Q30_threshold = 80
        elif read_length == 101:
            Q30_threshold = 75
        elif read_length == 151:
            Q30_threshold = 70
        elif read_length >= 251:
            Q30_threshold = 60 
    else:
        if read_length == 51:
            Q30_threshold = 85
        elif read_length == 101:
            Q30_threshold = 80
        elif read_length == 126:
            Q30_threshold = 80
        elif read_length == 151:
            Q30_threshold = 75
    
    if run_type == 'MiSeq':
        if read_length in [76, 301]:  
            exp_lane_clust = 18000000
        else:                               
            exp_lane_clust = 10000000
    else:
        if run_type in ['HiSeq Rapid Flow Cell v1','HiSeq Rapid Flow Cell v2', "TruSeq Rapid Flow Cell v2", "TruSeq Rapid Flow Cell v1"] :
            exp_lane_clust = 114000000
        elif run_type == 'HiSeq Flow Cell v3':
            exp_lane_clust = 143000000
        elif run_type == 'HiSeq Flow Cell v4':
            exp_lane_clust = 188000000
        elif run_type == 'HiSeqX10':
            exp_lane_clust = 250000000
    #Fix this! Should only be calculated once
    #exp_samp_clust = numpy.true_divide(exp_lane_clust, len(outarts_per_lane))
    exp_samp_clust = numpy.true_divide(exp_lane_clust, 3)        
    return Q30_threshold, int(exp_samp_clust*0.5), int(exp_samp_clust*0.1)
    
def manipulate_process(demux_process):
    demux_container = demux_process.all_inputs()[0].location[0].name
    
    workflow_types = {'MiSeq Run (MiSeq) 4.0':'Reagent Cartridge ID', 'Illumina Sequencing (Illumina SBS) 4.0':'Flow Cell ID',
              'Illumina Sequencing (HiSeq X) 1.0':'Flow Cell ID'}
    for k,v in workflow_types.items():
        workflow = lims.get_processes(udf = {v : demux_container}, type = k)
        #If workflow key exists
        if(workflow):
            seq_run = workflow[0]
            if 'MiSeq Run (MiSeq) 4.0' in k:
                run_type ='MiSeq'
            else:
                if 'Illumina Sequencing (Illumina SBS) 4.0' in k:
                    run_type = seq_run.udf['Flow Cell Version']
                elif 'Illumina Sequencing (HiSeq X) 1.0' in k:
                    run_type ='HiSeqX10'
            break
        
    proc_stats = dict(seq_run.udf.items())
    read_length = proc_stats['Read 1 Cycles']
    ##Set run threshold
    #Q30_threshold, reads_thres, undem_ind_thres = decide_thresholds(run_type, read_length)
    #proc_stats['Threshold for % bases >= Q30'] = Q30_threshold
    #proc_stats['Threshold for # Reads'] = reads_thres
    #proc_stats['Threshold for Undemultiplexed Index Yield'] = undem_ind_thres
    ##Put command for process 
    #demux_process.put()
    return demux_process, proc_stats, run_type
    
def set_sample_values(demux_process, parser_struct, proc_stats, run_type):
    #Sets sample values
    for pool in demux_process.all_inputs():
        outarts_per_lane = demux_process.outputs_per_input(pool.id, ResultFile = True)
        print len(outarts_per_lane)
        if run_type == 'Miseq':
            lane_no = '1'
        else:
            lane_no = pool.location[1][0]
        for target_file in outarts_per_lane:
            current_name = target_file.samples[0].name
            for entry in parser_struct:
                if lane_no == entry['Lane']:
                    sample = entry['Sample']
                    if sample == current_name:
                        target_file = {'%PF' : float(entry['% PFClusters']),
                        '% One Mismatch Reads (Index)' : float(entry['% One mismatchbarcode']),
                        '% of Raw Clusters Per Lane' : float(entry['% of thelane']),
                        'Ave Q Score' : float(entry['Mean QualityScore']),
                        '% Perfect Index Read' : float(entry['% Perfect Index Reads']),
                        'Yield (Mbases)' : numpy.true_divide(float(entry['Yield (Mbases)'].replace(',','')), 1000),
                        '% Bases >=Q30' : entry['% >= Q30bases'],
                        '# Reads' : entry['PF Clusters']}
                        if entry.has_key('Read 2 Cycles'):
                            target_file['# Read Pairs'] = numpy.true_divide(float(entry['PF Clusters']), 2)
                        else:
                            target_file['# Read Pairs'] = int(entry['PF Clusters'])
                        if ( proc_stats['Threshold for % bases >= Q30'] > float(entry['% >= Q30bases']) and 
                        proc_stats['Threshold for # Reads'] > entry['# Read Pairs'] ):
                            target_file['Include reads'] = 'YES'
                            target_file.qc_flag = 'PASSED'
                        else:
                            target_file['Include reads'] = 'NO'
                            target_file.qc_flag = 'FAILED'
            ##put here
            #target_file.put()
    
"""Creates demux_lims_id.csv and attaches it to process"""
#Handles undetermined quite badly, might be worth revising
#Path NEEDS to be based on id; but true path requires sync to mfs
#Is the lims id really necessary?? Could just get path from process and name the file w/e
def write_demuxfile(lanebc_lims_id, proc_stats):
    timestamp = datetime.fromtimestamp(time()).strftime('%Y-%m-%d_%H:%M')
    prefix = '/Users/isaksylvin/SciLifeLab/preprocExampleData'
    appendix = proc_stats['Run ID'], 'Demultiplexing/Reports/html/', proc_stats['Flow Cell ID'], 'all/all/all/laneBarcode.html'
    lanebc_path = prefix + appendix
    laneBC = classes.LaneBarcodeParser('/Users/isaksylvin/SciLifeLab/preprocExampleData/160115_ST-E00214_0074_AH7N7HCCXX/Demultiplexing/Reports/html/H7N7HCCXX/all/all/all/laneBarcode.html')
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
            writer.writerow([entry['Project'],entry['Sample'],entry['Lane'],reads,entry['Barcode sequence'],index_name,entry['% >= Q30bases']])
    return laneBC.sample_data
@click.command()
@click.option('--project_lims_id', required=True,help='REQUIRED: Lims ID of project. Example:24-92373')
@click.option('--lanebc_lims_id', help='REQUIRED: Lims ID for relevant laneBarcode.html. Example:92-570994')
@click.option('--log', default='log_file', 
              help='File name of log file used for runtime information and problems. Default:log_file') 
@click.option('--qc_log', default='qc_log_file', help='File name of log file used for quality control information and problems. Default:qc_log_file')    

#preproc 2, hiseq examples
#Preproc 1, hiseq X examples
#/srv/illumina/HiSeq_X_data/nosync/160115_ST-E00214_0074_AH7N7HCCXX
def main(project_lims_id, lanebc_lims_id, log, qc_log):
    lanebc_lims_id = '00testingYO'
    #Loggers needs to be implemented
    #Starts quality control log
    qc_log = open(qc_log, 'a')
    #Sets up the process values
    demux_process, proc_stats, run_type = manipulate_process(Process(lims,id = project_lims_id))
    #Create the attached csv file
    parser_struct = write_demuxfile(lanebc_lims_id, proc_stats)
    #Alters artifacts
    set_sample_values(demux_process, parser_struct, proc_stats, run_type)
               
if __name__ == '__main__':
    lims = Lims(BASEURI, USERNAME, PASSWORD)
    lims.check_version()
    #Omitting EppLogger. Steals my debug and Denis mentioned it's never checked.
    main()
