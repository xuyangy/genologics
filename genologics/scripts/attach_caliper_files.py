"""Python interface to GenoLogics LIMS via its REST API.

Usage example: Attach caliper image files to LIMS



Johannes Alneberg, Science for Life Laboratory, Stockholm, Sweden.
"""

from optparse import OptionParser
from pprint import pprint
from genologics.lims import Lims
from genologics.entities import Artifact, Process,Container, Sample
from shutil import copy

from genologics.config import BASEURI
import os



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
    

if __name__ == "__main__":
    parser = ArgumentParser()
    parser.add_argument('file',
           help='A caliper image to be uploaded to the Lims')
    parser.add_argument('--domain', default='.se',
                        help=('The domain used for the lims server,'
                              ' used for parsing out the file location,'
                              ' default=".se"'))
    args = parser.parse_args()

    lims = Lims(BASEURI,args.username,args.password)
    lims.check_version()
   
    #    fn = '27-4562_A1_P601_101_A1.png'
    #    fn_sv_edit = '27-4118_A1_P671_101_info_A1.png'
    assert os.path.isfile(args.file)
    fn = os.path.basename(args.file)
    print fn
    oa_1 = artifact_from_file_name(fn,lims)
    print oa_1
    r = allocate_resource_for_file(oa_1,args.file,lims)
    print r
    content_location = r.getchildren()[1].text
    print content_location
    move_file_to_lims(args.file,content_location,args.domain)
    data = lims.tostring(ElementTree.ElementTree(r))
    uri = lims.get_uri('files')
    lims.post(uri,data)
