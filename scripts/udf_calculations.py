#!/usr/bin/env python
"""EPP script to perform basic calculations on UDF:s in Clarity LIMS
Command to trigger this script:
bash -c "PATH/TO/INSTALLED/SCRIPT
--username {username} 
--password {password} 
--baseuri YOUR.URI 
--pid {processLuid} 
--log {compoundOutputFileLuidN}"
--output_files {outputFileLuids}
--udf1 NameOfUDF 1
--operator Mathematical operator
--udf2 NameOfUDF 2
--result_udf NameOfUDF to store result in
"

Johannes Alneberg, Science for Life Laboratory, Stockholm, Sweden
""" 
from argparse import ArgumentParser

from genologics.lims import Lims
from genologics.entities import Artifact
from genologics.epp import configure_logging,setup_standard_parser


def apply_calculations(lims,output_artifacts,udf1,op,udf2,result_udf):
    for artifact in output_artifacts:
        artifact[result_udf] = eval('{0}{1}{2}'.format(artifact.udf[udf1],op,artifact.udf[udf2]))
        artifact.put()

def main(lims,args):
    outputs = map(lambda id: Artifact(lims,id=id),args.output_files)
    for artifact in outputs:
        try:
            artifact.get()
        except:
            print "Unsuccesful get for artifact: {0}".format(artifact)
            raise
    apply_calculations(lims,outputs,args.udf1,args.operator,args.udf2,args.result_udf)


if __name__ == "__main__":
    # Initialize parser with standard arguments and description
    desc = """EPP script to perform basic calculations on UDF:s in Clarity LIMS.
    result_udf=udf1 *operator* udf2"""
    parser = setup_standard_parser(description=desc)

    # Additional arguments
    parser.add_argument('--output_files',nargs='*',
                        help='Lims unique ids for each output file artifact')
    parser.add_argument('--udf1',
                        help='The first udf in the formula')
    parser.add_argument('--operator', choices =['+','-'],
                        help='operator to apply')
    parser.add_argument('--udf2',
                        help='The second udf in the formula')
    parser.add_argument('--result_udf',
                        help='Udf to store the result')
    args = parser.parse_args()

    # Start logging
    if args.log:
        configure_logging(args.log)
    lims = Lims(args.baseuri,args.username,args.password)
    lims.check_version()

    main(lims, args)

