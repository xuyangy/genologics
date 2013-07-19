"""Python interface to GenoLogics LIMS via its REST API.

Usage example: EPP example script for Clarity LIMS.


Johannes Alneberg, Science for Life Laboratory, Stockholm, Sweden.
"""
from optparse import OptionParser

if __name__ == "__main__":
    parser = OptionParser()
    parser.add_option("--analyte_id", help="Input analyte id")
    (option,args) = parser.parse_args()
    print args
    print "Hello World!"
    print option

