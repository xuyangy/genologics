"""Python interface to GenoLogics LIMS via its REST API.

Usage example: Attach caliper image files to LIMS



Johannes Alneberg, Science for Life Laboratory, Stockholm, Sweden.
"""

from pprint import pprint
from genologics.lims import Lims
from genologics.entities import Artifact, Process,Container, Sample
from shutil import copy

from genologics.config import BASEURI, USERNAME, PASSWORD
import os

lims = Lims(BASEURI,USERNAME,PASSWORD)
lims.check_version()


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
    
if __name__ == "__main__":
    fn = '27-4562_A1_P601_101_A1.png'
    fn_sv_edit = '27-4118_A1_P671_101_info_A1.png'

    oa_1 = artifact_from_file_name(fn,lims)
    print oa_1

    oa_sv = artifact_from_file_name(fn_sv_edit,lims)
    print oa_sv
