#!/usr/bin/env python
DESC="""EPP script to aggregate the number of reads from different demultiplexing runs,
based on the flag 'include reads' located at the same level as '# reads' 

Denis Moreno, Science for Life Laboratory, Stockholm, Sweden
""" 
from argparse import ArgumentParser

from genologics.lims import Lims
from genologics.config import BASEURI,USERNAME,PASSWORD
from genologics.epp import EppLogger
import logging
import sys
from genologics.entities import *
from pprint import pprint


DEMULTIPLEX={'666' : 'Bcl Conversion & Demultiplexing (Illumina SBS) 4.0'}
SUMMARY = {'356' : 'Project Summary 1.3'}
def main(lims, args, logger):
   p = Process(lims,id = args.pid)
   for output_artifact in p.all_outputs():
       if output_artifact.type=='Analyte' and len(output_artifact.samples)==1:
           sample=output_artifact.samples[0]
           sample.udf['Total Reads (M)']=sumreads(sample)
           logging.info("Total reads is {0} for sample {1}".format(sample.udf['Total Reads (M)'],sample.name))
           sample.put()
       elif(output_artifact.type=='Analyte') and len(output_artifact.samples)!=1:
           logging.error("Found {0} samples for the ouput analyte {}, that should not happen".format(len(output_artifact.samples()),output_artifact.id))
            

def sumreads(sample):
    expectedName="{0} (FASTQ reads)".format(sample.name)
    arts=lims.get_artifacts(sample_name=sample.name,process_type=DEMULTIPLEX.values(), name=expectedName)   
    tot=0
    for a in sorted(arts, key=lambda art:art.parent_process.date_run):
        #discard artifacts that do not have reads
        #there should not be any actually
        if "# Reads" not in a.udf:
            continue
        try:
            if a.udf['Include reads'] == 'YES':
                tot+=float(a.udf['# Reads'])
        except KeyError:
            pass

    #grab the sequencing setup
    seqsetup=sample.project.udf.get('Sequencing setup')
    if seqsetup.startswith('2x'):
        #total needs to be divided by 2 
        tot/=2

    # total is displayed as millions
    tot/=1000000
    return tot

    

if __name__=="__main__":
    parser = ArgumentParser(description=DESC)
    parser.add_argument('--pid',
                        help='Lims id for current Process')
    parser.add_argument('--log',
                        help='Log file for runtime info and errors.')
    args = parser.parse_args()

    lims = Lims(BASEURI, USERNAME, PASSWORD)
    lims.check_version()

    main(lims, args, None)
    with EppLogger(args.log, lims=lims, prepend=True) as epp_logger:
        main(lims, args, epp_logger)
    #pj="P901"
    #samples=lims.get_samples(projectlimsid=pj)
    #samples=['P901_102']
    #for s in samples:
        #print "Sample {}".format(s)
        #updateSample(s)

