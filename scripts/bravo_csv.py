#!/usr/bin/env python
DESC="""EPP used to create csv files for the bravo robot"""

from argparse import ArgumentParser
from genologics.lims import Lims
from genologics.config import BASEURI,USERNAME,PASSWORD
from genologics.epp import attach_file, EppLogger
import logging
import re
from genologics.entities import *

def main(lims, args):
    currentStep=Process(lims,id=args.pid)
    for art_tuple in currentStep.input_output_maps:
        if art_tuple[0]['uri'].type=='Analyte' and art_tuple[1]['uri'].type=='Analyte': 
            source_fc=art_tuple[0]['uri'].location[0].name
            source_well=art_tuple[0]['uri'].location[1]
            dest_fc=art_tuple[1]['uri'].location[0].name
            dest_well=art_tuple[1]['uri'].location[1]
            volume=calc_vol(art_tuple)
            print art_tuple[0]['uri'].samples[0].name
            print "{0},{1},{2},{3},{4}".format(source_fc, source_well, volume, dest_fc, dest_well)

def calc_vol(art_tuple):
    try:
        assert art_tuple[0]['uri'].udf['Conc. Units'] == "ng/ul"
        amount_ng=art_tuple[1]['uri'].udf['Amount taken (ng)']
        conc=art_tuple[0]['uri'].udf['Concentration']
        return amount_ng/conc
    except KeyError as e:
        logging.error("The input artifact is lacking a field : {}".format(e)) 
    except AssertionError:
        logging.error("This script expects the concentration to be in ng/ul, this does not seem to be the case.")
    return "#ERROR#"

if __name__=="__main__":
    parser = ArgumentParser(description=DESC)
    parser.add_argument('--pid',
                        help='Lims id for current Process')
    parser.add_argument('--log',
                        help='Log file for runtime info and errors.')
    args = parser.parse_args()

    lims = Lims(BASEURI, USERNAME, PASSWORD)
    lims.check_version()
    main(lims, args)

