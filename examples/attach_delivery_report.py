"""Python interface to GenoLogics LIMS via its REST API.

Usage example: Attach customer delivery report to LIMS

NOTE: You need to set the BASEURI, USERNAME AND PASSWORD.

Roman Valls Guimera, Science for Life Laboratory, Stockholm, Sweden.
"""

import codecs
from genologics.lims import *

# Login parameters for connecting to a LIMS instance.
# NOTE: Modify according to your setup.
from genologics.site_cloud import BASEURI, USERNAME, PASSWORD

# Create the LIMS interface instance, and check the connection and version.
lims = Lims(BASEURI, USERNAME, PASSWORD)
lims.check_version()

# Get the list of all projects.
projects = lims.get_projects()

for prj in projects:
    print prj, prj.uri
