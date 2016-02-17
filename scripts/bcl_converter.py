"""Written by Isak Sylvin; isak.sylvin@scilifelab.se"""

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

def manipulate_process(demux_process):
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
            seq_run = workflow[0]
            if 'MiSeq Run (MiSeq) 4.0' in k:
                run_type ='MiSeq'
            elif 'Illumina Sequencing (Illumina SBS) 4.0' in k:
                run_type = seq_run.udf['Flow Cell Version']
            elif 'Illumina Sequencing (HiSeq X) 1.0' in k:
                run_type ='HiSeqX10'
            else:
                sys.exit("Unhandled prior workflow step (run type)")
            logging.info("Run type set to " + run_type)
            break
        
    #Set run thresholds
    thresholds = Thresholds('HiSeq', run_type, 'Single')
    Q30_thres = thresholds.Q30
    exp_lane_clust = thresholds.exp_lane_clust

    try:
        proc_stats = dict(seq_run.udf.items())
        if not proc_stats.has_key('Threshold for % bases >= Q30'):
            proc_stats['Threshold for % bases >= Q30'] = Q30_thres
        if not proc_stats.has_key('Expected reads per lane'):
            proc_stats['Expected reads per lane'] = exp_lane_clust
    except:
        sys.exit("Udf improperly formatted. Unable to set thresholds")
        
    logging.info("Q30 threshold set to " + str(Q30_thres))
    logging.info("Minimum clusters per lane set to " + str(exp_lane_clust))
    
    #demux_process.put()
    return demux_process, proc_stats, run_type
    
"""Sets artifact = samples values """
def set_sample_values(demux_process, parser_struct, proc_stats, run_type):
    for pool in demux_process.all_inputs():
        try:
            outarts_per_lane = demux_process.outputs_per_input(pool.id, ResultFile = True)
        except:
            sys.exit('Unable to fetch artifacts of process')
        if run_type == 'Miseq':
            lane_no = '1'
        else:
            try:
                lane_no = pool.location[1][0]
            except:
                sys.exit('Unable to determine lane number. Incorrect location variable in process.')
        logging.info("Lane number set to " + lane_no)
        exp_smp_per_lne = round(proc_stats['Expected reads per lane']/float(len(outarts_per_lane)), 0)
        logging.info('Expected sample clusters for this lane: ' + str(exp_smp_per_lne))
        for target_file in outarts_per_lane:
            try:
                current_name = target_file.samples[0].name
            except:
                sys.exit('Unable to determine sample name. Incorrect sample variable in process.')
            for entry in parser_struct:
                if lane_no == entry['Lane']:
                    sample = entry['Sample']
                    import pdb
                    pdb.set_trace()
                    #Goofball stuff going on here; since we request lims ID
                    #current anme = lims; sample is from local data
                    if sample == current_name:
                        try:
                            target_file.udf = {'%PF' : float(entry['% PFClusters']),
                            '% One Mismatch Reads (Index)' : float(entry['% One mismatchbarcode']),
                            '% of Raw Clusters Per Lane' : float(entry['% of thelane']),
                            'Ave Q Score' : float(entry['Mean QualityScore']),
                            '% Perfect Index Read' : float(entry['% Perfect Index Reads']),
                            'Yield (Mbases)' : float(entry['Yield (Mbases)'].replace(',',''))/1000,
                            '% Bases >=Q30' : entry['% >= Q30bases'],
                            '# Reads' : entry['PF Clusters']}
                        except:
                            sys.exit("Unable to set artifact values.")
                        logging.info('Added the following set of values to artifact:')
                        logging.info(target_file.udf['%PF'] + ' %PF')
                        logging.info(target_file.udf['% One Mismatch Reads (Index)'] + ' % One Mismatch Reads (Index)')
                        logging.info(target_file.udf['% of Raw Clusters Per Lane'] + ' % of Raw Clusters Per Lane')
                        logging.info(target_file.udf['Ave Q Score'] + ' Ave Q Score')
                        logging.info(target_file.udf['% Perfect Index Read'] + ' % Perfect Index Read')
                        logging.info(target_file.udf['Yield (Mbases)'] + ' Yield (Mbases)')
                        logging.info(target_file.udf['% Bases >=Q30'] + ' % Bases >=Q30')
                        logging.info(target_file.udf['# Reads'] + ' # Reads')
                        
                        try:
                            if ( proc_stats['Threshold for % bases >= Q30'] > float(entry['% >= Q30bases']) and 
                            exp_smp_per_lne > entry['# Reads'] ):
                                target_file.udf['Include reads'] = 'YES'
                                target_file.qc_flag = 'PASSED'
                                logging.info('Sample passed defined thresholds')
                            else:
                                target_file.udf['Include reads'] = 'NO'
                                target_file.qc_flag = 'FAILED'
                                logging.info('Sample failed to pass defined thresholds')
                        except:
                            sys.exit("Unable to set QC status for sample")
                        
            #target_file.put()
    
#Handles undetermined quite badly, might be worth revising
"""Creates demux_lims_id.csv and attaches it to process"""
def write_demuxfile(proc_stats):
    prefix = '/Users/isaksylvin/SciLifeLab/preprocExampleData/'
    try:
        appendix = proc_stats['Run ID'] + '/Demultiplexing/Reports/html/' + proc_stats['Flow Cell ID'] + '/all/all/all/laneBarcode.html'
    except:
        sys.exit("Unable to set demux filename. Udf does not contain keys for run id and/or flowcell id.")
    lanebc_path = prefix + appendix
    #change to lanebc_path once done
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
            try:
                writer.writerow([entry['Project'],entry['Sample'],entry['Lane'],reads,entry['Barcode sequence'],index_name,entry['% >= Q30bases']])
            except:
                sys.exit("Flowcell parser is unable to fetch all necessary fields for demux file.")
    return laneBC.sample_data
@click.command()
@click.option('--project_lims_id', required=True,help='REQUIRED: Lims ID of project. Example:24-92373')
@click.option('--rt_log', default='stdout_'+ timestamp + '.log', 
              help='File name to log runtime information (mostly errors). Default:stdout_TIME.log') 
@click.option('--qc_log', default='qc_metrics_' + timestamp + '.log', help='File name of to log quality control metrics. Default:qc_metrics_TIME.log')    

#preproc 2, hiseq examples
#Preproc 1, hiseq X examples
#/srv/illumina/HiSeq_X_data/nosync/160115_ST-E00214_0074_AH7N7HCCXX
def main(project_lims_id, rt_log, qc_log):
    #Change when running
    lanebc_lims_id = '00testingYO'
    #Starts quality control log
    logging.basicConfig(filename=qc_log,level=logging.INFO)
    #Sets up the process values
    demux_process, proc_stats, run_type = manipulate_process(Process(lims,id = project_lims_id))
    #Create the attached csv file
    parser_struct = write_demuxfile(proc_stats)
    #Alters artifacts
    set_sample_values(demux_process, parser_struct, proc_stats, run_type)
               
if __name__ == '__main__':
    lims = Lims(BASEURI, USERNAME, PASSWORD)
    lims.check_version()
    #Omitting EppLogger. Steals my debug and Denis mentioned it's never checked.
    main()
