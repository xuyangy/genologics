"""Python interface to GenoLogics LIMS via its REST API.

Usage example: Attach caliper image files to LIMS



Johannes Alneberg, Science for Life Laboratory, Stockholm, Sweden.
"""

from optparse import OptionParser
from pprint import pprint
from genologics.lims import Lims
from genologics.entities import Artifact, Process,Container, Sample
from shutil import copy

from argparse import ArgumentParser
import os
import sys
import re

import logging

class NotFoundError(Exception):
    """Exception raised if certain item is not found in the Clarity Lims.
    
    Attributes:
        entity -- entity that was looked for
        q_key  -- query key
        q_val  -- query value
        fn     -- file name
    """

    def __init__(self,entity,q_key,q_val,fn):
        self.entity = entity
        self.q_key = q_key
        self.q_val = q_val
        self.fn = fn

    def __str__(self):
        s =  ("No %(entity)s found with query key '%(q_key)s' "
              "and query value '%(q_val)s', parsed from file name %(fn)s.") % \
            {'entity':self.entity.__name__, 
             'q_key':self.q_key,
             'q_val':self.q_val,
             'fn':self.fn}
        return s


class MultipleFoundError(Exception):
    """Exception raised if multiple items are found where uniqueness was assumed
    
    Attributes:
        entity -- entity that was looked for
        q_key  -- query key
        q_val  -- query value
        fn     -- file name
    """

    def __init__(self,entity,q_key,q_val,fn):
        self.entity = entity
        self.q_key = q_key
        self.q_val = q_val
        self.fn = fn

    def __str__(self):
        s =  ("Multiple %(entity)s was found with query key '%(q_key)s' "
              "and query value '%(q_val)s', parsed from file name %(fn)s.") % \
            {'entity':self.entity.__name__, 
             'q_key':self.q_key,
             'q_val':self.q_val,
             'fn':self.fn}
        return s

def attach_file(src,artifact):
    original_name = os.path.basename(src)
    new_name = artifact.id + '_' + original_name
    dir = os.getcwd()
    location = os.path.join(dir,new_name)
    print "Moving {0} to {1}".format(src,location)
    copy(src,location)
    
 
class StreamToLogger(object):
   """
   Fake file-like stream object that redirects writes to a logger instance.
   
   source: 
   http://www.electricmonk.nl/log/2011/08/14/
   redirect-stdout-and-stderr-to-a-logger-in-python/
   """
   def __init__(self, logger, log_level=logging.INFO):
      self.logger = logger
      self.log_level = log_level
      self.linebuf = ''
 
   def write(self, buf):
      for line in buf.rstrip().splitlines():
         self.logger.log(self.log_level, line.rstrip())
 
def configure_logging(logging,log_file):
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s:%(levelname)s:%(name)s:%(message)s',
        filename=log_file,
        filemode='a'
        )
    stdout_logger = logging.getLogger('STDOUT')
    sl = StreamToLogger(stdout_logger, logging.INFO)
    sys.stdout = sl
    
    stderr_logger = logging.getLogger('STDERR')
    sl = StreamToLogger(stderr_logger, logging.ERROR)
    sys.stderr = sl

def main(lims,pluid,path):
    p = Process(lims,id=args.pluid)
    
    file_list = os.listdir(args.path)
    
    io = p.input_output_maps
    io_filtered = filter(lambda (x,y): y['output-generation-type']=='PerInput',io)
    
    for input,output in io_filtered:
        i_a = Artifact(lims,id=input['limsid'])
        o_a = Artifact(lims,id=output['limsid'])
        if len(i_a.samples)==0:
            raise NotFoundError(None,None,None,None)
        elif len(i_a.samples)!=1:
            raise MultipleFoundError(None,None,None,None)
        i_s=i_a.samples[0]
        i_c = i_a.location[0]
        im_file_r = re.compile('^{container}.+{sample}.+\.(png|pdf|PNG)'.format(container=i_c.id,sample=i_s.name))
        fns = filter(im_file_r.match,file_list)
        print "Looking for files with container id {0} and sample name {1}".format(i_c.id,i_s.name)
        if len(fns)==0:
            raise NotFoundError(None,None,None,None)
        elif len(fns)!=1:
            raise MultipleError(None,None,None,None)
        fn = fns[0]
        print "Found image file {0}".format(fn)
        fp = os.path.join(args.path,fn)
        
        attach_file(fp,o_a)
        
    

if __name__ == "__main__":
    parser = ArgumentParser()
    parser.add_argument('--username',
                        help='The user name')
    parser.add_argument('--password',
                        help='Password')
    parser.add_argument('--baseuri',
                        help='Uri for the lims server')
    parser.add_argument('--pluid',
                        help='Process Lims Id')
    parser.add_argument('--path',
                        help='Path where image files are located')
    parser.add_argument('-l','--log',default=None,
                        help='Log file')
    args = parser.parse_args()
 
    if args.log:
        configure_logging(logging,args.log)

    lims = Lims(args.baseuri,args.username,args.password)
    lims.check_version()

    main(lims,args.pluid,args.path)
