"""Python interface to GenoLogics LIMS via its REST API.

Usage example: EPP example script for Clarity LIMS.


Johannes Alneberg, Science for Life Laboratory, Stockholm, Sweden.
"""
from optparse import OptionParser
from genologics.lims import Lims
from genologics.entities import Process

if __name__ == "__main__":
    parser = OptionParser()
    parser.add_option("--analyte_id", help="Input analyte id")
    parser.add_option("--baseuri", help="Base uri for your lims server")
    parser.add_option("--username", help="User name")
    parser.add_option("--password", help="User password")
    parser.add_option("--pid", help="Process id") 
    (option,args) = parser.parse_args()
    print args
    lims = Lims(option.baseuri,option.username,option.password)
    lims.check_version() 
    p=Process(lims,id=option.pid)
    print option.pid
    print p.input_output_maps[0]
    print [(input['limsid'],output['limsid']) for (input,output) in p.input_output_maps]
