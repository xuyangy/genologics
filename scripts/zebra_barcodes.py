#!/usr/bin/env python
import sys
from argparse import ArgumentParser
import subprocess
import logging
from genologics.config import BASEURI,USERNAME,PASSWORD
from genologics.lims import Lims
from genologics.epp import EppLogger


def construct(*args, **kwargs):
    start = int(kwargs.get('start'))
    end = int(kwargs.get('end'))
    
    for i in range(start, end):
        PID = "P"+str(i)
        makeProjectBarcode(PID)
    
def makeProjectBarcode(PID):
    print "^XA" #start of label
    print "^DFFORMAT^FS" #download and store format, name of format, end of field data (FS = field stop)
    print "^LH0,0" # label home position (label home = LH)
    print "^FO360,20^AFN,60,20^FN1^FS" #AF = assign font F, field number 1 (FN1), print text at position field origin (FO) rel. to home
    print "^FO140,5^BCN,70,N,N^FN2^FS" #BC=barcode 128, field number 2, Normal orientation, height 70, no interpreation line. 
    print "^XZ" #end format
    
    for i in range (1,6):
        PlateID="P"+str(i)
        plateCode=PID+PlateID
        print "^XA" #start of label format
        print "^XFFORMAT^FS" #label home posision
        print "^FN1^FD"+plateCode+"^FS" #this is readable
        print "^FN2^FD"+plateCode+"^FS" #this is the barcode
        print "^XZ"

def makeContainerBarcode(plateid,copies=1):
    lines = []
    lines.append("^XA") #start of label
    lines.append("^DFFORMAT^FS") #download and store format, name of format, end of field data (FS = field stop)
    lines.append("^LH0,0") # label home position (label home = LH)
    lines.append("^FO360,20^AFN,60,20^FN1^FS") #AF = assign font F, field number 1 (FN1), print text at position field origin (FO) rel. to home
    lines.append("^FO70,5^BCN,70,N,N^FN2^FS") #BC=barcode 128, field number 2, Normal orientation, height 70, no interpreation line. 
    lines.append("^XZ") #end format

    for copy in xrange(copies):
        lines.append("^XA") #start of label format
        lines.append("^XFFORMAT^FS") #label home posision
        lines.append("^FN1^FD"+plateid+"^FS") #this is readable
        lines.append("^FN2^FD"+plateid+"^FS") #this is the barcode
        lines.append("^XZ")
    return lines
    
def getArgs():
    description = ("Print barcodes on zebra barcode printer "
                   "for NGI Genomics Projects.")
    parser = ArgumentParser(description=description)
    parser.add_argument('--plateid',
                        help='The plate ID to print on the barcode.')
    parser.add_argument('--log',
                        help='File name to use as log file')
    parser.add_argument('--printout',action="store_true",
                        help=('Print file on default or '
                              'supplied printer using lp command.'))
    parser.add_argument('--hostname',
                        help='Hostname for lp CUPS server.')
    parser.add_argument('--destination',
                        help='Name of printer.')
    parser.add_argument('--copies', default=1, type=int,
                        help='Number of printout copies')
    return parser.parse_args()

def main(args,epp_logger):
    lines = []
    if args.plateid is not None:
        logging.info('Constructing container barcode.')
        lines += makeContainerBarcode(args.plateid, copies=args.copies)
    if not args.printout:
        logging.info('Writing to stdout.')
        epp_logger.saved_stdout.write('\n'.join(lines)+'\n')
    elif lines:
        lp_args = ["lp"]
        if args.hostname:
            lp_args += ["-h",args.hostname]
        if args.destination:
            lp_args += ["-d",args.destination]
        lp_args.append("-") # lp accepts stdin if '-' is given as filename
        logging.info('Ready to call lp for printing.')
        sp = subprocess.Popen(lp_args, 
                              stdin=subprocess.PIPE, 
                              stdout=subprocess.PIPE, 
                              stderr=subprocess.PIPE)
        sp.stdin.write(str('\n'.join(lines)))
        logging.info('lp command is called for printing.')
        stdout,stderr = sp.communicate() # Will wait for sp to finish
        logging.info('lp stdout: {0}'.format(stdout))
        logging.info('lp stderr: {0}'.format(stderr))
        logging.info('lp command finished')
        sp.stdin.close()

if __name__ == '__main__':
    arguments = getArgs()
    lims = Lims(BASEURI,USERNAME,PASSWORD)
    lims.check_version()
    with EppLogger(arguments.log,lims=lims,prepend=False) as epp_logger:
        main(arguments,epp_logger)
