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

# Allocate location at the LIMS server
#original_location='/home/johannes/repos/genologics/test_data/2-26065.JPG'
#assert os.path.isfile(original_location)
#response = lims.post_file(artifact,original_location)

#print response


fn = '27-4562_A1_P601_101_A1.png'
fn_rna = '27-1893_E2_P189_113_info_L9.png'
fn_sv = 'P671P1_A1_P671_101_A1.png'
fn_sv_edit = '27-4118_A1_P671_101_info_A1.png'

def process_from_file_name(fn,lims):
    fn_l = fn.split('_')
    input_container = Container(lims,id=fn_l[0])
    try:
        input_container.get()
    except:
        raise Exception(
            "No container found with id %(id)s, parsed from file name %(fn)s." % {id:fn_l[0],fn:fn}
    input_sample_name = fn_l[2]+'_'+fn_l[3]
    input_samples = lims.get_samples(name=input_sample_name)
    if len(input_samples) != 1:
        if len(input_samples) == 0:
            raise Exception(
                "No sample found with name %(name)s, parsed from file name %(fn)s." % {name:input_sample_name,fn:fn} )
        else:
            raise Exception(
                "Non unique sample for name %(name)s, parsed from file name %(fn)s." % {name:input_sample_name,fn:fn} )

    input_sample = input_samples[0]
    input_artifacts = lims.get_artifacts(containerlimsid=input_container.id,sample_name=input_sample_name)

    if len(input_artifacts) != 1:
        if len(input_artifacts) == 0:
            raise Exception(
                """No artifact found with container lims id %(cid)s,
                   sample name %(sn)s, 
                   parsed from file name %(fn)s.""" % {'cid':input_container.id,'sn':input_sample_name, 'fn':fn} )
        else:
            raise Exception(
                """Non unique artifacts was found with container lims id %(cid)s,
                   sample name %(sn)s, 
                   parsed from file name %(fn)s.""" % {'cid':input_container.id,'sn':input_sample_name, 'fn':fn} )
        

    input_artifact = input_artifacts[0]
    # Find the correct process
    processes_for_input_artifact = lims.get_processes(inputartifactlimsid=input_artifact.id)
    processes_for_type_dna_and_project = lims.get_processes(projectname=input_sample.project.name,type='CaliperGX QC (DNA)')
    processes_for_type_rna_and_project = lims.get_processes(projectname=input_sample.project.name,type='CaliperGX QC (RNA)')


    process_ids_input = set([prc.id for prc in processes_for_input_artifact])
    process_ids_dna = set([prc.id for prc in processes_for_type_dna_and_project])
    process_ids_rna = set([prc.id for prc in processes_for_type_rna_and_project])

    ids = (process_ids_input & process_ids_dna) | (process_ids_input & process_ids_rna)
    if len(ids) != 1:
        if len(ids) == 0:
            raise Exception(
                """No process found with container lims id %(cid)s,
                   sample name %(sn), 
                   parsed from file name %(fn)s.""" % {'cid':input_container,'sn':input_sample_name, 'fn':fn} )
        else:
            raise Exception(
                """Non unique artifacts was found with container lims id %(cid)s,
                   sample name %(sn), 
                   parsed from file name %(fn)s.""" % {'cid':input_container,'sn':input_sample_name, 'fn':fn} )
        

    process = Process(lims,id =ids.pop())
    
    in_id_out_id = {}
    for input,output in process.input_output_maps:
        if output['output-generation-type'] == 'PerInput':
            in_id_out_id[input['limsid']]=output['limsid']
    output_artifact = Artifact(lims,id=in_id_out_id[input_artifact.id])

    return process,output_artifact
    

pr_1,oa_1 = process_from_file_name(fn,lims)

print pr_1,oa_1
pr_2,oa_2 = process_from_file_name(fn_rna,lims)
print pr_2,oa_2

pr_sv,oa_sv = process_from_file_name(fn_sv_edit,lims)
print pr_sv,oa_sv
