#!/usr/bin/env python
DESC="""EPP script to copy the "Comments" field to the projects running notes on process termination

Denis Moreno, Science for Life Laboratory, Stockholm, Sweden
""" 
from argparse import ArgumentParser
from genologics.entities import *
from genologics.lims import Lims
from genologics.config import BASEURI,USERNAME,PASSWORD
from genologics.epp import attach_file, EppLogger
from LIMS2DB.objectsDB import process_categories as pc

import datetime
import logging
import os
import sys
import json




def main(lims, args):
    
    PROJECT_LEVEL = pc.AGRLIBVAL.values() + pc.AGRINITQC.values()
    FLOWCELL_LEVEL = pc.SEQUENCING.values()

    comment=False

    noteobj={}
    pro=Process(lims, id=args.pid)
    if 'Comments' in pro.udf and pro.udf['Comments'] is not '':
        key=datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")
        noteobj[key]={}
        note="Comment from {0} ({1}) : {2}".format(pro.type.name, '[LIMS](http://genologics.scilifelab.se:8080/clarity/work-details/{0})'.format(pro.id.split('-')[1]), pro.udf['Comments'])
        noteobj[key]['note']=note
        noteobj[key]['user']="{0} {1}".format(pro.technician.first_name,pro.technician.last_name)
        noteobj[key]['email']=pro.technician.email
        noteobj[key]['category']='Comment'
        comment=True

    step = Step(lims, id = args.pid)
    if step.actions.escalation:
        key=datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")
        noteobj[key]={}
        note="Escalation request from process {0} ({1}) {2}".format(pro.type.name, '[LIMS](http://genologics.scilifelab.se:8080/clarity/work-details/{0})'.format(pro.id.split('-')[1]), step.actions.escalation['request'])
        noteobj[key]['note']=note
        noteobj[key]['user']="{0} {1}".format(pro.technician.first_name,pro.technician.last_name)
        noteobj[key]['email']=pro.technician.email
        noteobj[key]['category']='Escalation'
        comment=True
        

    if comment:
        if pro.type.name in PROJECT_LEVEL: 
            #find the correct projects.
            samples=set()
            projects=set()
            for inp in pro.all_inputs():
                #bitwise or to add inp.samples to samplesas a set
                samples |= set(inp.samples)
            for sam in samples:
                projects.add(sam.project)

            for proj in projects:
                if 'Running Notes' in proj.udf:
                    existing_notes=json.loads(proj.udf['Running Notes'])
                    for key in noteobj:
                        existing_notes[key]=noteobj[key]
                    proj.udf['Running Notes']=json.dumps(existing_notes)
                else:
                    proj.udf['Running Notes']=json.dumps(noteobj) 
                proj.put()
        elif pro.type.name in FLOWCELL_LEVEL: 
            cont=pro.all_inputs()[0].location[0]
            if 'Notes' in cont.udf:
                existing_notes=json.loads(cont.udf['Notes'])
                for key in noteobj:
                    existing_notes[key]=noteobj[key]
                cont.udf['Notes']=json.dumps(existing_notes)
            else:
                cont.udf['Notes']=json.dumps(noteobj) 
            cont.put()

            
if __name__=="__main__":
    parser = ArgumentParser(description=DESC)
    parser.add_argument('--pid',
                        help='Lims id for current Process')
    args = parser.parse_args()

    lims = Lims(BASEURI, USERNAME, PASSWORD)
    lims.check_version()

    main(lims, args)
