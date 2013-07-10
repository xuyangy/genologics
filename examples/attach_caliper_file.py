"""Python interface to GenoLogics LIMS via its REST API.

Usage example: Attach customer delivery report to LIMS



Johannes Alneberg, Science for Life Laboratory, Stockholm, Sweden.
"""

from pprint import pprint
from genologics.lims import Lims
from genologics.entities import Artifact, Glsstorage, File
from shutil import copy
from xml.etree import ElementTree

from genologics.config import BASEURI, USERNAME, PASSWORD
import os

lims = Lims(BASEURI,USERNAME,PASSWORD)
lims.check_version()

artifact = Artifact(lims,id='92-26375')

print 'UDFs:'
pprint(artifact.udf.items())

print 'Files:'
pprint(artifact.files)

print 'Artifact uri:'
pprint(artifact.uri)

# Allocate location at the LIMS server
original_location='/home/johannes/repos/genologics/test_data/2-26065.JPG'
assert os.path.isfile(original_location)
response = lims.post_file(artifact,original_location)

print response
