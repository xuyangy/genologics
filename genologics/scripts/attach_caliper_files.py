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

#print response


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

def _file_dict(p):
    """ Constructs a mapping from input container, input sample to image file

    p: Path where images are stored
    """
    # Regular expression will match at least 4 underscores and
    # file extension png, pdf or PNG.
    im_file_r = re.compile('^.+_.+_.+_.+_.+\.(png|pdf|PNG)')
    d = {}
    for fn in os.listdir(p):
        if im_file_r.match(fn):
            fn_l = fn.split('_')
            cn=fn_l[0]
            sn=fn_l[2]+'_'+fn_l[3]
            if (cn,sn) in d:
                raise MultipleFoundError(None,None,None,None)
            d[(cn,sn)]=fn
    return d

def artifact_from_file_name(fn,lims):
    fn_l = fn.split('_')
    input_container = Container(lims,id=fn_l[0])
    try:
        input_container.get()
    except:
        raise NotFoundError(Container,'id',fn_l[0],fn)
    input_sample_name = fn_l[2]+'_'+fn_l[3]
    input_samples = lims.get_samples(name=input_sample_name)
    if len(input_samples) != 1:
        if len(input_samples) == 0:
            raise NotFoundError(Sample,'name',input_sample_name,fn)
        else:
            raise MultipleFoundError(Sample,'name',input_sample_name,fn)
        

    input_sample = input_samples[0]
    input_artifacts = lims.get_artifacts(containerlimsid=input_container.id,
                                         sample_name=input_sample_name)

    if len(input_artifacts) != 1:
        if len(input_artifacts) == 0:
            raise NotFoundError(Artifact,
                                'container lims id, input sample name',
                                (input_container.id,input_sample_name),
                                fn)
        else:
            raise MultipleFoundError(Artifact,
                                'container lims id, input sample name',
                                (input_container.id,input_sample_name),
                                fn)

    input_artifact = input_artifacts[0]
    # Find the correct process
    prcs_input_art = lims.get_processes(inputartifactlimsid=input_artifact.id)
    prcs_dna_and_project = lims.get_processes(
        projectname=input_sample.project.name,
        type='CaliperGX QC (DNA)')
    prcs_rna_and_project = lims.get_processes(
        projectname=input_sample.project.name,
        type='CaliperGX QC (RNA)')


    prc_ids_input = set([prc.id for prc in prcs_input_art])
    prc_ids_dna = set([prc.id for prc in prcs_dna_and_project])
    prc_ids_rna = set([prc.id for prc in prcs_rna_and_project])

    ids = (prc_ids_input & prc_ids_dna) | (prc_ids_input & prc_ids_rna)
    if len(ids) != 1:
        if len(ids) == 0:
            raise NotFoundError(Process,
                                'container lims id, sample name',
                                (input_container.id,input_sample_name),
                                fn)

        else:
            raise MultipleFoundError(Process,
                                'container lims id, sample name',
                                (input_container.id,input_sample_name),
                                fn)

    process = Process(lims,id =ids.pop())
    
    in_id_out_id = {}
    for input,output in process.input_output_maps:
        if output['output-generation-type'] == 'PerInput':
            in_id_out_id[input['limsid']]=output['limsid']
    output_artifact = Artifact(lims,id=in_id_out_id[input_artifact.id])

    return output_artifact
    
def allocate_resource_for_file(attached_instance,file_path,lims):
    from xml.etree import ElementTree

    node = ElementTree.Element('file:file')
    node.attrib['xmlns:file'] = "http://genologics.com/ri/file"
    
    at = ElementTree.SubElement(node,'attached-to')
    at.text = attached_instance.uri
    
    ol = ElementTree.SubElement(node,'original-location')
    ol.text = file_path

    data = lims.tostring(ElementTree.ElementTree(node))
    uri = lims.get_uri('glsstorage')

    r = lims.post(uri,data)
    return r

def move_file_to_lims(src,content_location,domain):
    location = content_location.split(domain)[1]

    location_path = os.path.abspath(location)

    if not os.path.exists(location_path):
        print os.path.abspath(location)
        os.makedirs(os.path.abspath(location))
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
        logging.basicConfig(
            level=logging.DEBUG,
            format='%(asctime)s:%(levelname)s:%(name)s:%(message)s',
            filename=args.log,
            filemode='a'
            )
        stdout_logger = logging.getLogger('STDOUT')
        sl = StreamToLogger(stdout_logger, logging.INFO)
        sys.stdout = sl
 
        stderr_logger = logging.getLogger('STDERR')
        sl = StreamToLogger(stderr_logger, logging.ERROR)
        sys.stderr = sl

    lims = Lims(args.baseuri,args.username,args.password)
    lims.check_version()
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
        print ("Looking for files with container id {0} and sample name {1}".format(i_c.id,i_s.name))
        if len(fns)==0:
            raise NotFoundError(None,None,None,None)
        elif len(fns)!=1:
            raise MultipleError(None,None,None,None)
        fn = fns[0]
        fp = os.path.join(args.path,fn)
        
        r = allocate_resource_for_file(o_a,fp,lims)
        content_location=r.getchildren()[1].text
        move_file_to_lims(fp,content_location,'.se')
        data = lims.tostring(ElementTree.ElementTree(r))
        uri = lims.get_uri('files')
        lims.post(uri,data)
        
