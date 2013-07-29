#!/usr/bin/env python
from argparse import ArgumentParser
from genologics.lims import Lims
from genologics.entities import Project
from genologics.epp import configure_logging
import yaml
import sys

example_info={'details': [{'algorithm': {'aligner': 'novoalign',
                                         'quality_format': 'Standard',
                                         'variantcaller': 'gatk'},
                           'analysis': 'variant2',
                           'description': 'Sample 1',
                           'files': ['/path/to/1_1-fastq.txt', '/path/to/1_2-fastq.txt'],
                           'genome_build': 'GRCh37'},
                          {'analysis': 'Minimal',
                           'description': 'Multiplex example',
                           'genome_build': 'hg19',
                           'multiplex': [{'barcode_id': 1,
                                          'barcode_type': 'Illumina',
                                          'name': 'One Barcode Sample',
                                          'sequence': 'ATCACG'},
                                         {'barcode_id': 2,
                                          'barcode_type': 'Illumina',
                                          'name': 'Another Barcode Sample',
                                          'sequence': 'CGATGT'}]}],
              'fc_date': '110812',
              'fc_name': 'unique_name',
              'upload': {'dir': '../final'}}

default_info={'details': [{'algorithm': {'aligner': 'novoalign',
                                         'quality_format': 'Standard',
                                         'variantcaller': 'gatk'},
                           'analysis': 'variant2',
                           'description': 'Sample 1',
                           'files': ['/path/to/1_1-fastq.txt', '/path/to/1_2-fastq.txt'],
                           'genome_build': 'GRCh37'},
                          {'analysis': 'Minimal',
                           'description': 'Multiplex example',
                           'genome_build': 'hg19',
                           'multiplex': [{'barcode_id': 1,
                                          'barcode_type': 'Illumina',
                                          'name': 'One Barcode Sample',
                                          'sequence': 'ATCACG'},
                                         {'barcode_id': 2,
                                          'barcode_type': 'Illumina',
                                          'name': 'Another Barcode Sample',
                                          'sequence': 'CGATGT'}]}],
              'fc_date': '110812',
              'fc_name': 'unique_name',
              'upload': {'dir': '../final'}}

def main(lims,projectid,outfile):
    p = Project(lims,id=projectid)
    try:
        a = p.udf['Application']
    except:
        sys.stderr.write(('Error while collecting Application udf from project '
                          'with id{0}').format(projectid))
        raise
    default_info['details'][1]['analysis'] = a
    fh = open(outfile,'w+')
    yaml.dump(default_info,fh,default_flow_style=False)

if __name__=="__main__":
    parser = ArgumentParser()
    parser.add_argument('--username',
                        help='The user name')
    parser.add_argument('--password',
                        help='Password')
    parser.add_argument('--baseuri',
                        help='Uri for the lims server')
    parser.add_argument('--pid',
                        help='Process Lims Id')
    parser.add_argument('-l','--log',default=None,
                        help='Log file')
    parser.add_argument('--projectid',
                        help='Project id to generate info for')
    parser.add_argument('--outfile',
                        help='Name of outputfile')
    args = parser.parse_args()

    if args.log:
        configure_logging(args.log)

    lims = Lims(args.baseuri,args.username,args.password)
    lims.check_version()

    main(lims,args.projectid,args.outfile)
