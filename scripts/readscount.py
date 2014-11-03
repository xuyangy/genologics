#!/usr/bin/env python
DESC="""EPP script to aggregate the number of reads from different demultiplexing runs,
based on the flag 'include reads' located at the same level as '# reads' 

Denis Moreno, Science for Life Laboratory, Stockholm, Sweden
""" 
from argparse import ArgumentParser

from genologics.lims import Lims
from genologics.config import BASEURI,USERNAME,PASSWORD
from genologics.epp import attach_file, EppLogger
import logging
import sys
import os
from genologics.entities import *


DEMULTIPLEX={'13' : 'Bcl Conversion & Demultiplexing (Illumina SBS) 4.0'}
SUMMARY = {'356' : 'Project Summary 1.3'}
SEQUENCING = {'38' : 'Illumina Sequencing (Illumina SBS) 4.0','46' : 'MiSeq Run (MiSeq) 4.0'}
def main(lims, args, logger):
    """This should be run at project summary level"""
    p = Process(lims,id = args.pid)
    samplenb=0
    errnb=0
    summary={}
    logart=None
    for output_artifact in p.all_outputs():
        #filter to only keep solo sample demultiplexing output artifacts
        if output_artifact.type=='Analyte' and len(output_artifact.samples)==1:
            sample=output_artifact.samples[0]
            samplenb+=1
            #update the total number of reads
            sample.udf['Total Reads (M)']=sumreads(sample, summary)
            logging.info("Total reads is {0} for sample {1}".format(sample.udf['Total Reads (M)'],sample.name))
            try:
                if sample.udf['Reads Min'] > sample.udf['Total Reads (M)']:
                    sample.udf['Status (auto)']="In Progress"
                elif sample.udf['Reads Min'] < sample.udf['Total Reads (M)'] : 
                    sample.udf['Passed Sequencing QC']="True"
                    sample.udf['Status (auto)']="Finished"
            except KeyError as e:
                print e
                logging.warning("No reads minimum found, cannot set the status auto flag for sample {}".format(sample.name))
                errnb+=1

            #commit the changes
            sample.put()
        elif(output_artifact.type=='Analyte') and len(output_artifact.samples)!=1:
            logging.error("Found {0} samples for the ouput analyte {1}, that should not happen".format(len(output_artifact.samples()),output_artifact.id))
        elif(output_artifact.type=="ResultFile" and output_artifact.name=="AggregationLog"):
            logart=output_artifact


    #write the csv file, separated by pipes, no cell delimiter
    with open("AggregationLog.csv", "w") as f:
        f.write("sample name | number of flowcells | number of lanes | flowcell1:lane1,lane2;flowcell2:lane1,lane2,lane3 ...")
        for sample in summary:
            view=set("{0}:{1}".format(f, summary[sample][f].join(",")) for f in summary[sample])
            totfc=len(summary[sample])
            totlanes=0
            for f in summary[sample]:
                totlanes+=len(summary[sample][f])
            f.write("{0} | {1} | {2} | {3}\n".format(sample, totfc, totlanes, ";".join(view)))
    attach_file(os.path.join(os.getcwd(), "AggregationLog.csv"), logart)
    logging.info("updated {0} samples with {1} errors".format(samplenb, errnb))
            
def demnumber(sample):
    """Returns the number of distinct demultiplexing processes tagged with "Include reads" for a given sample"""
    expectedName="{0} (FASTQ reads)".format(sample.name)
    dem=set()
    arts=lims.get_artifacts(sample_name=sample.name,process_type=DEMULTIPLEX.values(), name=expectedName)   
    for a in arts:
        if a.udf["Include reads"] == "YES":
            dem.add(a.parent_process.id)
    return len(dem)
    
def sumreads(sample, summary):
    if sample.name not in summary:
        summary[sample.name]={}
    expectedName="{0} (FASTQ reads)".format(sample.name)
    arts=lims.get_artifacts(sample_name=sample.name,process_type=DEMULTIPLEX.values(), name=expectedName)   
    tot=0
    fileteredarts=[]
    base_art=None
    for a in sorted(arts, key=lambda art:art.parent_process.date_run):
        if "# Reads" not in a.udf:
            continue
        try:
            if a.udf['Include reads'] == 'YES':
                orig=a.parent_process.all_inputs()
                for o in orig:
                    if sample in o.samples:
                        #if the artifact belongs to the same flowcell/run, overwrite with the most recent.
                        fc="{0}:{1}".format(o.location[0].name,o.location[1].split(":")[0])
                        if o.location[0] in summary[sample.name]:
                            summary[sample.name][o.location[0]].append(o.location[1].split(":")[0])
                        else:
                            summary[sample.name][o.location[0]]=[o.location[1].split(":")[0]]

                        filteredarts.append(a)
        except KeyError:
            #Happens if the "Include reads" does not exist
            pass

    for a in filteredarts:
        base_art=a
        tot+=float(a.udf['# Reads'])

    #grab the sequencing process associated 
    #find the correct input
    inputart=None
    try:
        for inart in base_art.parent_process.all_inputs():
            if sample.name in [s.name for s in inart.samples]:
                try:
                    sq=lims.get_processes(type=SEQUENCING.values(), inputartifactlimsid=inart.id)
                except TypeError:
                    logging.error("Did not manage to get sequencing process for artifact {}".format(inart.id))
                else:
                    if "Read 2 Cycles" in sq.udf and sq.udf['Read 2 Cycles'] is not None:
                        tot/=2
                break
    except AttributeError:
        #base_art is still None because no arts were found
        logging.info("No demultiplexing processes found for sample {0}".format(sample.name))



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

