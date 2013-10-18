#!/usr/bin/env python
DESC = """EPP script to copy user defined field 'Status (manual)' from analyte 
level to  submitted sample level in Clarity LIMS. Can be executed in the 
background or triggered by a user pressing a "blue button".

This script can only be applied to processes where ANALYTES are modified in 
the GUI. The script can output two different logs, where the status_changelog 
contains notes with the technician, the date and changed status for each 
copied status. The regular log file contains regular execution information. 

Error handling:
If the udf 'Status (manual)' is blank or not defined for any of the inputs,
the script will log this, and not perform any changes for that artifact.


Written by Johannes Alneberg, Science for Life Laboratory, Stockholm, Sweden
""" 

from argparse import ArgumentParser

from genologics.lims import Lims
from genologics.config import BASEURI,USERNAME,PASSWORD

from genologics.entities import Process, Artifact
from genologics.epp import EppLogger

import logging
import sys

from shutil import copy
import os

class Session(object):
    def __init__(self, process, udf, changelog=None):
        self.process = process
        self.udf = udf
        self.technician = self.process.technician
        self.changelog = changelog
    
    def _current_time(self):
        return strftime("%Y-%m-%d %H:%M:%S", time.localtime())
        
    def _sample_udf(self,artifact):
        s = self._sample(artifact)

        if self.udf in s.udf:
            return s.udf[self.udf]
        else:
            return "Undefined"

    def _sample(self,artifact):
        return artifact.samples[0]

    def log_before_change(self, artifact, changelog_f=None):
        if changelog_f:
            d = {'ct' : self._current_time(),
                 'tn' : self.technician.name,
                 'ti' : self.technician.id,
                 'udf': self.udf,
                 'su' : self._sample_udf(artifact),
                 'nv' : artifact.udf[self.udf]
                 }

            changelog_f.write(("{ct}: Technician {tn} (id: {ti}),"
                               "sample {udf} from "
                               "{su} to status {nv}").format(d))

        logging.info(("Copying from artifact with id: {0} to sample with "
                      " id: {1}").format(artifact.id, self.sample().id))

    def log_after_change(self, artifact, saved_sample_udf):
        d = {'udf': self.udf,
             'su': saved_sample_udf,
             'nv': artifact.udf[udf]
             }

        logging.info("Updated Sample {0} from {1} to {2}.".format(d))

    def copy_udf(self,artifact, changelog_f = None):
        self.log_before_change(artifact, changelog_f)
        
        saved_sample_udf = self._sample_udf(artifact)

        sample = self._sample(artifact)
        sample.udf[udf] = artifact.udf[udf]
        sample.put()

        self.log_after_change(artifact, saved_sample_udf)

    def copy_main(self, artifacts):
        if self.changelog:
            with open(self.changelog, 'a') as changelog_f:
                for artifact in artifacts:
                    self.copy_udf(artifact, changelog_f)
        else:
            for artifact in artifacts:
                self.copy_udf(artifact)


def check_udf_is_defined(artifacts,udf):
    """ Filter and Warn if udf is not defined for any of inputs. """
    filtered_artifacts = []
    incorrect_artifacts = []
    for artifact in artifacts:
        if (udf in artifact.udf):
            filtered_artifacts.append(artifact)
        else:
            logging.warning(("Found artifact for sample {0} with {1} "
                             "undefined/blank, exiting").format(input.samples[0].name,udf))
            incorrect_artifacts.append(artifact)
    return filtered_artifacts, incorrect_artifacts

def prepend_status_changelog(args):
    """ Prepends old file entries if such exists """
    # Check if a changelog for this process exists: 
    try:
        changelog_artifact = Artifact(lims, id=args.status_changelog)
        changelog_artifact.get()
        if changelog_artifact.files:
            changelog_path = changelog_artifact.files[0].content_location.split(
                self.lims.baseuri.split(':')[1])[1]
            dir = os.getcwd()
            destination = os.path.join(dir, args.status_changelog)
            copy(changelog_path,destination)
            with open(destination, 'a') as f:
                f.write('='*80+'\n')
    except HTTPError: # Probably no artifact found, skip prepending
        logging.warning(('No changelog file artifact found '
                         'for id: {0}').format(args.status_changelog))
    except IOError as e: # Probably some path was wrong in copy
        logging.error(('Changelog could not be prepended, '
                       'make sure {0} and {1} are '
                       'proper paths.').format(changelog_path))
        sys.exit(-1)

def main(lims,args,epp_logger):
    p = Process(lims,id = args.pid)
    update_udf = 'Status (manual)'
    artifacts = p.all_inputs(unique=True)
    correct_artifacts, incorrect_udf = check_udf_is_defined(artifacts, update_udf)

    if args.status_changelog:
        prepend_status_changelog(args)

    if correct_artifacts:
        session = Session(p,update_udf, changelog=args.status_changelog)
        session.copy_main(correct_artifacts)

    d = {'ca': len(correct_artifacts),
    'ia': len(incorrect_artifacts),
    'warning' : len(incorrect_artifacts) or "WARNING "
    }

    abstract = ("Updated {ca} artifact(s), {warning} skipped {ia} "
    "artifact(s) with incorrect udf info.").format(d)

    print >> sys.stderr, abstract # stderr will be logged and printed in GUI


if __name__ == "__main__":
    # Initialize parser with standard arguments and description

    parser = ArgumentParser(description=DESC)
    parser.add_argument('--pid',
                        help='Lims id for current Process')
    parser.add_argument('--log',default=sys.stdout,
                        help=('File name for standard log file, '
                              ' for runtime information and problems.'))
    parser.add_argument('--status_changelog',
                        help=('File name for status changelog file, '
                              ' for concise information on who, what and '
                              ' when for status change events. '
                              'Prepends the old changelog file by default.'))
    args = parser.parse_args()

    lims = Lims(BASEURI,USERNAME,PASSWORD)
    lims.check_version()

    with EppLogger(args.log,lims=lims, prepend=True) as epp_logger:
        main(lims, args, epp_logger)
