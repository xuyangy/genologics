"""Python interface to GenoLogics LIMS via its REST API.

Usage example: Attach customer delivery report to LIMS



Johannes Alneberg, Science for Life Laboratory, Stockholm, Sweden.
"""

from pprint import pprint
from genologics.lims import Lims
from genologics.entities import Artifact

from genologics.config import BASEURI, USERNAME, PASSWORD

lims = Lims(BASEURI,USERNAME,PASSWORD)
lims.check_version()

artifact = Artifact(lims,id='2-26065')

print 'UDFs:'
pprint(artifact.udf.items())

print 'Files:'
pprint(artifact.files)
