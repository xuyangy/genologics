#!/usr/bin/env python
DESC="""EPP used to create csv files for the bravo robot"""

from argparse import ArgumentParser
from genologics.lims import Lims
from genologics.config import BASEURI,USERNAME,PASSWORD
from genologics.epp import attach_file, EppLogger
import logging
import os
import sys
from genologics.entities import *


MAX_WARNING_VOLUME=150
MIN_WARNING_VOLUME=2

def obtain_previous_volumes(currentStep, lims):
    samples_volumes={}
    sn_re=re.compile("(P[0-9]+_[0-9]+)")
    previous_steps=set()
    for input_artifact in currentStep.all_inputs():
        previous_steps.add(input_artifact.parent_process)
        for pp in previous_steps:
            for output in pp.all_outputs():
                if output.name == "Normalization buffer volumes CSV":
                    try:
                        fid=output.files[0].id
                    except:
                        raise RuntimeError
                    else:
                        file_contents=lims.get_file_contents(id=fid)
                        sname_idx=0
                        source_vol_idx=5
                        buffer_vol_idx=11
                        read=False
                        for line in file_contents.split('\n') :
                            if not line.rstrip():
                                read=False
                            if "Sample Name" in line:
                                read=True
                                #header line
                                elements=line.split(',')
                                for idx, el in enumerate(elements):
                                    if el == "Source Volume (uL)":
                                        source_vol_idx=idx
                                    elif el == "Volume of Dilution Buffer (uL)":
                                        buffer_vol_idx=idx
                                    elif el == "Sample Name":
                                        sname_idx=idx
                            elif read:
                                elements=line.split(',')
                                samplename=elements[sname_idx]
                                if samplename[0] == '"' and samplename[-1] == '"':
                                    samplename=samplename[1:-1]

                                matches=sn_re.search(samplename)
                                if matches:
                                    samplename=matches.group(1)


                                srcvol=elements[source_vol_idx]
                                if srcvol[0] == '"' and srcvol[-1] == '"':
                                    srcvol=srcvol[1:-1]
                                srcvol=float(srcvol)
                                bufvol=elements[buffer_vol_idx]
                                if bufvol[0] == '"' and bufvol[-1] == '"':
                                    bufvol=bufvol[1:-1]
                                bufvol=float(bufvol)

                                samples_volumes[samplename]=srcvol+bufvol

    return samples_volumes



def make_datastructure(currentStep, lims, log):
    data=[]

    try:
        samples_volumes=obtain_previous_volumes(currentStep, lims)
    except:
        log.append("Unable to find previous volumes")

    for inp, out in currentStep.input_output_maps:
        if out['output-type'] == 'Analyte':
            obj={}
            obj['name']=inp['uri'].samples[0].name
            obj['id']=inp['uri'].id
            obj['conc']=inp['uri'].udf['Normalized conc. (nM)']
            obj['pool_id']=out['uri'].id
            #obj['pool_conc']=out['uri'].udf['Normalized conc. (nM)']
            obj['vol']=samples_volumes[obj['name']]
            obj['src_fc']=inp['uri'].location[0].id
            obj['src_well']=inp['uri'].location[1]
            obj['dst_fc']=out['uri'].location[0].id
            obj['dst_well']=out['uri'].location[1]
            data.append(obj)

    return data

######### LAZY WAY ###############################
# Just divide the total with the number of samples, it is implied that the final
# conc and the conc of every input is the same:
def lazy_volumes(samples, final_vol):
    return [final_vol / len(samples) for s in samples]

######### OTHER WAY ##############################
# Iteratively reduce the smallest input volume until we are close to the desired
# total volume. This works when the inputs have different concentrations, the
# final pool concentration will then end up somewhere between the conc of the
# highest and the lowest input concentration:
def optimize_volumes(samples, final_vol, limit_vol=2):
    # Create a list we can sort to get the min/max values:
    l = [(s["conc"]*s["vol"],s["conc"],s["vol"]) for s in samples]
    # Find the min/max values by sorting on the different values:
    min_conc = sorted(l, key=lambda x: x[1])[0][1]
    max_conc = sorted(l, key=lambda x: x[1])[-1][1]
    min_vol = sorted(l, key=lambda x: x[2])[0][2]
    # The volume of the input with lowest amount:
    min_amount = sorted(l)[0][2]

    def _minimize_vol(vol, final_vol=final_vol, limit_vol=limit_vol, reduce=0.9):
        try_vol = reduce * vol
        # The lowest volume to take would then be (sample(s) w highest conc):
        low_vol = min(try_vol * max_conc / s["conc"] for s in samples)
        # Total pool volume if we were to take this amount of all samples:
        tot_vol = sum(try_vol * max_conc / s["conc"] for s in samples)
        # We don't want to pipette less than limit_vol
        # while keeping total volume above final_vol:
        if low_vol >= limit_vol and tot_vol >= final_vol and try_vol >= limit_vol:
            return _minimize_vol(try_vol)
        else:
            # We can't improve anymore within the given limits... 
            return vol

    # Start from whichever is the smallest volume:
    use_vol = _minimize_vol(min(min_amount, min_vol))
    # Calculate the volume to take of each input:
    return [(use_vol * max_conc / s["conc"]) for s in samples]

def compute_transfer_volume(currentStep, lims, log):
    data=make_datastructure(currentStep, lims, log)
    returndata=[]
    for pool in currentStep.all_outputs():
        if pool.type == 'Analyte':
            valid_inputs=[x for x in data if x['pool_id']==pool.id]
            # Set the output conc of the pool and also get the "desired" pool
            # volume, which is which? 
            final_vol = pool.udf["Maximal Volume (uL)"] # Change to "Final Volume (uL)"
            conc = valid_inputs[0]["conc"]
            # If all inputs are of the same conc use the trivial algorithm,
            # else try to optimize:
            if all(s["conc"] == conc for s in valid_inputs):
                vols = lazy_volumes(valid_inputs, final_vol)
                pool.udf['Normalized conc. (nM)'] = conc
            else:
                vols = optimize_volumes(valid_inputs, final_vol, MIN_WARNING_VOLUME)
                # Calculate and add the theoretical pool conc:
                z = list(zip([s["conc"] for s in valid_inputs], vols))
                v = (sum(x[0]*x[1] for x in z) / sum(vols))
                pool.udf['Normalized conc. (nM)'] = v
            pool.put()
            for s, vol in zip(valid_inputs, vols):
                s['vol_to_take'] = vol
                returndata.append(s)

    return returndata

def prepooling(currentStep, lims):
    log=[]
    #First thing to do is to grab the volumes of the input artifacts. The method is ... rather unique.
    data=compute_transfer_volume(currentStep, lims, log)
    with open("bravo.csv", "w") as csvContext:
            for s in data:
                if s['vol_to_take']>MAX_WARNING_VOLUME:
                    log.append("Volume for sample {} is above {}, redo the calculations manually".format(MAX_WARNING_VOLUME, s['name']))
                if s['vol_to_take']<MIN_WARNING_VOLUME:
                    log.append("Volume for sample {} is below {}, redo the calculations manually".format(MIN_WARNING_VOLUME, s['name']))
                csvContext.write("{0},{1},{2},{3},{4}\n".format(s['src_fc'], s['src_well'], s['vol_to_take'], s['dst_fc'], s['dst_well'])) 
    if log:
        with open("bravo.log", "w") as logContext:
            logContext.write("\n".join(log))
    for out in currentStep.all_outputs():
        #attach the csv file and the log file
        if out.name=="Bravo CSV File":
            attach_file(os.path.join(os.getcwd(), "bravo.csv"), out)
        if log and out.name=="Bravo Log":
            attach_file(os.path.join(os.getcwd(), "bravo.log"), out)
    if log:
        #to get an eror display in the lims, you need a non-zero exit code AND a message in STDERR
        sys.stderr.write("Errors were met, please check the Log file\n")
        sys.exit(2)
    else:
        logging.info("Work done")

def setup_workset(currentStep):
    checkTheLog=[False]
    with open("bravo.csv", "w") as csvContext:
        with open("bravo.log", "w") as logContext:
            #working directly with the map allows easier input/output handling
            for art_tuple in currentStep.input_output_maps:
                #filter out result files
                if art_tuple[0]['uri'].type=='Analyte' and art_tuple[1]['uri'].type=='Analyte': 
                    source_fc=art_tuple[0]['uri'].location[0].name
                    source_well=art_tuple[0]['uri'].location[1]
                    dest_fc=art_tuple[1]['uri'].location[0].id
                    dest_well=art_tuple[1]['uri'].location[1]
                    try:
                        #might not be filled in
                        final_volume=art_tuple[1]['uri'].udf["Total Volume (uL)"]
                    except KeyError as e:
                        logContext.write("No Total Volume found for sample {0}\n".format(art_tuple[0]['uri'].samples[0].name))
                        checkTheLog[0]=True
                    else:
                        volume=calc_vol(art_tuple, logContext, checkTheLog)
                        csvContext.write("{0},{1},{2},{3},{4},{5}\n".format(source_fc, source_well, volume, dest_fc, dest_well, final_volume)) 
    for out in currentStep.all_outputs():
        #attach the csv file and the log file
        if out.name=="Bravo CSV File":
            attach_file(os.path.join(os.getcwd(), "bravo.csv"), out)
        if out.name=="Bravo Log":
            attach_file(os.path.join(os.getcwd(), "bravo.log"), out)
    if checkTheLog[0]:
        #to get an eror display in the lims, you need a non-zero exit code AND a message in STDERR
        sys.stderr.write("Errors were met, please check the Log file\n")
        sys.exit(2)
    else:
        logging.info("Work done")

def main(lims, args):
    #Array, so can be modified inside a child method
    currentStep=Process(lims,id=args.pid)
    if "Setup" in currentStep.type.name or "Genotyping" in currentStep.type.name:
        setup_workset(currentStep)
    elif "Pooling" in currentStep.type.name:
        prepooling(currentStep, lims)



def calc_vol(art_tuple, logContext,checkTheLog):
    try:
        #not handling different units yet. Might be needed at some point.
        assert art_tuple[0]['uri'].udf['Conc. Units'] == "ng/ul"
        amount_ng=art_tuple[1]['uri'].udf['Amount taken (ng)']
        conc=art_tuple[0]['uri'].udf['Concentration']
        volume=float(amount_ng)/float(conc)
        if volume<MIN_WARNING_VOLUME:
            #arbitrarily determined by Sverker Lundin
            logContext.write("WARN : Sample {0} located {1} {2}  has a LOW volume : {3}\n".format(art_tuple[1]['uri'].samples[0].name,
                art_tuple[0]['uri'].location[0].name,art_tuple[0]['uri'].location[1], volume))
            checkTheLog[0]=True
        elif volume>art_tuple[0]['uri'].udf["Volume (ul)"]:
            #check against the "max volume"
            logContext.write("WARN : Sample {0} located {1} {2}  has a HIGH volume : {3}, over {4}\n".format(art_tuple[1]['uri'].samples[0].name, 
                art_tuple[0]['uri'].location[0].name, art_tuple[0]['uri'].location[1], volume,art_tuple[0]['uri'].udf["Volume (ul)"] ))
            checkTheLog[0]=True
        elif volume>art_tuple[1]['uri'].udf['Total Volume (uL)']:
            logContext.write("WARN : Sample {0} located {1} {2}  has a HIGHER volume than the total: {3}, over {4}\n".format(art_tuple[1]['uri'].samples[0].name, 
                art_tuple[0]['uri'].location[0].name, art_tuple[0]['uri'].location[1], volume,art_tuple[1]['uri'].udf["Total Volume (uL)"] ))
            checkTheLog[0]=True
        else:
            logContext.write("INFO : Sample {0} looks okay.\n".format(art_tuple[1]['uri'].samples[0].name))
        return "{0:.2f}".format(volume) 
    except KeyError as e:
        logContext.write("ERROR : The input artifact is lacking a field : {0}\n".format(e)) 
        checkTheLog[0]=True
    except AssertionError:
        logContext.write("ERROR : This script expects the concentration to be in ng/ul, this does not seem to be the case.\n")
        checkTheLog[0]=True
    #this allows to still write the file. Won't be readable though
    return "#ERROR#"

if __name__=="__main__":
    parser = ArgumentParser(description=DESC)
    parser.add_argument('--pid',
                        help='Lims id for current Process')
    args = parser.parse_args()

    lims = Lims(BASEURI, USERNAME, PASSWORD)
    lims.check_version()
    main(lims, args)
