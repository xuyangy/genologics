#!/usr/bin/env python
DESC = """EPP script to copy user defined field from analyte 
level to  submitted sample level in Clarity LIMS. Can be executed in the 
background or triggered by a user pressing a "blue button".

This script can only be applied to processes where ANALYTES are modified in 
the GUI. The script can output two different logs, where the status_changelog 
contains notes with the technician, the date and changed status for each 
copied status. The regular log file contains regular execution information. 

Error handling:
If the udf given is blank or not defined for any of the inputs,
the script will log this, and not perform any changes for that artifact.


Written by Johannes Alneberg, Science for Life Laboratory, Stockholm, Sweden
""" 

from argparse import ArgumentParser

from genologics.lims import Lims
from genologics.config import BASEURI,USERNAME,PASSWORD

from genologics.entities import Process, Artifact
from genologics.epp import EppLogger
from genologics.lims_utils import CopyField

import logging
import sys

from shutil import copy
import os

from time import strftime, localtime
from requests import HTTPError



def main(lims, argsi, epp_logger):
    correct_artifacts = []
    incorrect_artifacts = []
    used_artifacts = []
    p = Process(lims,id = args.pid)
        
    if args.aggregate:
        artifacts = p.all_inputs(unique=True)
    else:
        artifacts = p.all_outputs(unique=True)
        artifacts = filter(lambda a: a.type == 'Analyte', artifacts)

    if args.status_changelog:
        dir = os.getcwd()
        destination = os.path.join(dir, args.status_changelog)
        if not os.path.isfile(destination):
            epp_logger.prepend_old_log(args.status_changelog)

    with open(args.status_changelog, 'a') as changelog_f:
        for artifact in artifacts:
            if args.source_udf in artifact.udf:
                correct_artifacts.append(artifact)
                copy_sesion = CopyField(artifact, artifact.samples[0], args.source_udf, args.dest_udf)
                try: 
                    copy_sesion.copy_udf(changelog_f)
                    used_artifacts.append(artifact)
                except:
                    pass
            else:
                incorrect_artifacts.append(artifact)
                logging.warning(("Found artifact for sample {0} with {1} "
                                "undefined/blank, exiting").format(artifact.samples[0].name,args.source_udf))

    if len(incorrect_artifacts) == 0:
        warning = "no artifacts"
    else:
        warning = "WARNING: skipped {0} artifact(s)".format(len(incorrect_artifacts))
        
    d = {'ua': len(used_artifacts),
         'ca': len(correct_artifacts),
         'ia': len(incorrect_artifacts),
         'warning' : warning}

    abstract = ("Updated {ua} artifact(s), out of {ca} in total, "
                "{warning} with incorrect udf info.").format(**d)

    print >> sys.stderr, abstract # stderr will be logged and printed in GUI


if __name__ == "__main__":
    parser = ArgumentParser(description=DESC)
    parser.add_argument('--pid',
                        help='Lims id for current Process')
    parser.add_argument('--log',
                        help=('File name for standard log file, '
                              ' for runtime information and problems.'))
    parser.add_argument('-s', '--source_udf', type=str, default=None,
                        help=('Name of the source user defined field that will'
                              'be copied.'))
    parser.add_argument('-d', '--dest_udf', type=str, default=None,
                        help=('Name of the destination user defined field that will'
                              'be written to. This argument is optional, if left empty'
                              'the source_udf argument is used instead.'))
    parser.add_argument('-c', '--status_changelog',
                        help=('File name for status changelog file, '
                              ' for concise information on who, what and '
                              ' when for status change events. '
                              'Prepends the old changelog file by default.'))
    parser.add_argument('-a', '--aggregate', default=False, action="store_true",
                        help=("Use this tag if your process is aggregating "
                              "results. The default behaviour assumes it is "
                              "the output artifact of type analyte that is "
                              "modified while this tag changes this to using "))
    args = parser.parse_args()

    lims = Lims(BASEURI,USERNAME,PASSWORD)
    lims.check_version()

    with EppLogger(args.log, lims=lims, prepend=True) as epp_logger:
        main(lims, args, epp_logger)
