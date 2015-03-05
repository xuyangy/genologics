#!/usr/bin/env python
DESC="""EPP used to create csv files for the bravo robot"""

from argparse import ArgumentParser
from genologics.lims import Lims
from genologics.config import BASEURI,USERNAME,PASSWORD
from genologics.epp import attach_file, EppLogger
import logging
import os
import sys
from genologics.entities import *


def main(lims, args):
    #Array, so can be modified inside a child method
    checkTheLog=[False]
    currentStep=Process(lims,id=args.pid)
    with open("bravo.csv", "w") as csvContext:
        with open("bravo.log", "w") as logContext:
            #working directly with the map allows easier input/output handling
            for art_tuple in currentStep.input_output_maps:
                #filter out result files
                if art_tuple[0]['uri'].type=='Analyte' and art_tuple[1]['uri'].type=='Analyte': 
                    source_fc=art_tuple[0]['uri'].location[0].name
                    source_well=art_tuple[0]['uri'].location[1]
                    dest_fc=art_tuple[1]['uri'].location[0].name
                    dest_well=art_tuple[1]['uri'].location[1]
                    try:
                        #might not be filled in
                        final_volume=art_tuple[1]['uri'].udf["Total Volume (uL)"]
                    except KeyError as e:
                        logContext.write("No Total Volume found for sample {0}\n".format(art_tuple[0]['uri'].samples[0].name))
                        checkTheLog[0]=True
                    else:
                        volume=calc_vol(art_tuple, logContext, checkTheLog)
                        csvContext.write("{0},{1},{2},{3},{4},{5}\n".format(source_fc, source_well, volume, dest_fc, dest_well, final_volume)) 
    for out in currentStep.all_outputs():
        #attach the csv file and the log file
        if out.name=="Bravo CSV File":
            attach_file(os.path.join(os.getcwd(), "bravo.csv"), out)
        if out.name=="Bravo Log":
            attach_file(os.path.join(os.getcwd(), "bravo.log"), out)
    if checkTheLog[0]:
        #to get an eror display in the lims, you need a non-zero exit code AND a message in STDERR
        sys.stderr.write("Errors were met, please check the Log file\n")
        sys.exit(2)
    else:
        logging.info("Work done")
def calc_vol(art_tuple, logContext,checkTheLog):
    try:
        #not handling different units yet. Might be needed at some point.
        assert art_tuple[0]['uri'].udf['Conc. Units'] == "ng/ul"
        amount_ng=art_tuple[1]['uri'].udf['Amount taken (ng)']
        conc=art_tuple[0]['uri'].udf['Concentration']
        volume=amount_ng/conc
        if volume<2:
            #arbitrarily determined by Joel Gruselius
            logContext.write("WARN : Sample {0} located {1} {2}  has a LOW volume : {3}\n".format(art_tuple[1]['uri'].samples[0].name,
                art_tuple[0]['uri'].location[0].name,art_tuple[0]['uri'].location[1], volume))
            checkTheLog[0]=True
        elif volume>art_tuple[0]['uri'].udf["Volume (ul)"]:
            #check against the "max volume"
            logContext.write("WARN : Sample {0} located {1} {2}  has a HIGH volume : {3}, over {4}\n".format(art_tuple[1]['uri'].samples[0].name, 
                art_tuple[0]['uri'].location[0].name, art_tuple[0]['uri'].location[1], volume,art_tuple[0]['uri'].udf["Volume (ul)"] ))
            checkTheLog[0]=True
        elif volume>art_tuple[1]['uri'].udf['Total Volume (uL)']:
            logContext.write("WARN : Sample {0} located {1} {2}  has a HIGHER volume than the total: {3}, over {4}\n".format(art_tuple[1]['uri'].samples[0].name, 
                art_tuple[0]['uri'].location[0].name, art_tuple[0]['uri'].location[1], volume,art_tuple[0]['uri'].udf["Total Volume (uL)"] ))
            checkTheLog[0]=True
        else:
            logContext.write("INFO : Sample {0} looks okay.\n".format(art_tuple[1]['uri'].samples[0].name))
        return "{0:.2f}".format(volume) 
    except KeyError as e:
        logContext.write("ERROR : The input artifact is lacking a field : {0}\n".format(e)) 
        checkTheLog[0]=True
    except AssertionError:
        logContext.write("ERROR : This script expects the concentration to be in ng/ul, this does not seem to be the case.\n")
        checkTheLog[0]=True
    #this allows to still write the file. Won't be readable though
    return "#ERROR#"

if __name__=="__main__":
    parser = ArgumentParser(description=DESC)
    parser.add_argument('--pid',
                        help='Lims id for current Process')
    args = parser.parse_args()

    lims = Lims(BASEURI, USERNAME, PASSWORD)
    lims.check_version()
    main(lims, args)

