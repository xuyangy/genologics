#!/usr/bin/env python
DESC = """This EPP script reads demultiplex end undemultiplexed yields from file
system and then does the following

1)  Sets the output artifact udfs based demultiplex resultfile.
 
2)  Sets the output artifact qc-flaggs based on the threshold-udfs if the process: 
        % Perfect Index Reads < 60 (default)
        %Q30 < 80 (default)
        expected index < 0.1 M (default)

3)  Warns if anny unexpected index has yield > 0.5M

4)  Loads a result file with demultiplex end undemultiplexed yields. This should
    be checked if warnings are given.

Reads from:
    --files--
    Demultiplex_Stats.htm                           in mfs file system
    Undemultiplexed_stats.metrics                   in mfs file system

Writes to:
    --Lims fields--
    qc-flag                                         per artifact (result file)
    % One Mismatch Reads (Index)                    per artifact (result file)
    % of Raw Clusters Per Lane                      per artifact (result file)
    %PF                                             per artifact (result file)
    Ave Q Score                                     per artifact (result file)
    Yield PF (Gb)                                   per artifact (result file)
    % Perfect Index Read                            per artifact (result file)
    % Bases >=Q30                                   per artifact (result file)
    # Reads                                         per artifact (result file)
    # Read Pairs

Logging:
    The script outputs a regular log file with regular execution information.

Written by Maya Brandi 
"""

import os
import sys
import logging
import glob
import csv
import numpy as np

from argparse import ArgumentParser
from genologics.lims import Lims
from genologics.config import BASEURI, USERNAME, PASSWORD
from genologics.entities import Process
from genologics.epp import EppLogger
from genologics.epp import set_field
from qc_parsers import FlowcellRunMetricsParser

class UndemuxInd():
    def __init__(self, process):
        self.process = process
        self.input_pools = process.all_inputs()
        self.dem_stat = None
        self.QC_fail = []
        self.undem_stat = None 
        self.abstract = []
        self.nr_lane_samps_updat = 0
        self.nr_lane_samps_tot = 0
        self.seq_run = None
        self.single = True
        self.file_path = None
        self.run_udfs = {}
        self.demux_udfs = dict(self.process.udf.items())
        self.read_length = None
        self.Q30_treshold = None
        self.high_index_yield = []
        self.high_lane_yield = []
        self.html_file_error = False
        self.qc_log_file = None

    def get_run_info(self):
        try:
            cont_name = self.process.all_inputs()[0].location[0].name
        except:
            sys.exit('Could not find container name.')
        miseq = lims.get_processes(
                                udf={'Reagent Cartridge ID' : cont_name},
                                type = 'MiSeq Run (MiSeq) 4.0')
        hiseq = lims.get_processes(
                                udf = {'Flow Cell ID' : cont_name},
                                type = 'Illumina Sequencing (Illumina SBS) 4.0')
        hiseq_X10 = lims.get_processes(
                                udf = {'Flow Cell ID' : cont_name},
                                type = 'Illumina Sequencing (HiSeq X) 1.0')
        if miseq:
            self.seq_run = miseq[0]
            self.run_type = 'MiSeq'
        elif hiseq:
            self.seq_run = hiseq[0]
            try:
                self.run_type = self.seq_run.udf['Flow Cell Version']
            except:
                sys.exit("Missing field 'Flow Cell Version' in sequencing process")
            path_id = cont_name
        elif hiseq_X10:
            self.seq_run = hiseq_X10[0]
            self.run_type = 'HiSeqX10'
            path_id = cont_name
        else:
            sys.exit("run not found")
        self.run_udfs = dict(self.seq_run.udf.items())
        self._get_run_id()
        self._get_cycles()
        self._get_file_path(cont_name)
        self._get_demultiplex_files()
        self._get_threshold_Q30()

    def _get_run_id(self):
        if self.run_udfs.has_key('Run ID'):
            self.process.udf['Run ID'] = self.run_udfs['Run ID']
            set_field(self.process)

    def _get_cycles(self):
        if self.run_udfs.has_key('Read 1 Cycles'):
            self.read_length = self.run_udfs['Read 1 Cycles']
        else:
            sys.exit("Could not get 'Read 1 Cycles' from the sequencing step.")
        if self.run_udfs.has_key('Read 2 Cycles'):
            self.single = False

    def _get_file_path(self, cont_name):
        if self.run_type == 'MiSeq':
            path_id = self.run_udfs['Flow Cell ID']
            data_folder = 'miseq_data'
        elif self.run_type == 'HiSeqX10':
            path_id = cont_name
            data_folder = 'HiSeq_X_data'
        else:
            data_folder = 'hiseq_data'
            path_id = cont_name
        try:
            self.file_path = glob.glob(("/srv/mfs/{0}/*{1}/Unaligned/"
                                        "Basecall_Stats_*/".format(data_folder, path_id)))[0]
        except:
            sys.exit("Failed to get file path")

    def _get_demultiplex_files(self):
        """ Files are read from the file msf system. Path hard coded."""
        FRMP = FlowcellRunMetricsParser()
        try:
            fp_dem = self.file_path + 'Demultiplex_Stats.htm'
            self.dem_stat = FRMP.parse_demultiplex_stats_htm(fp_dem)
            logging.info("Parsed file {0}".format(fp_dem))
        except:
            sys.exit("Failed to find or parse Demultiplex_Stats.htm.")
        try:
            fp_und = self.file_path + 'Undemultiplexed_stats.metrics'
            self.undem_stat = FRMP.parse_undemultiplexed_barcode_metrics(fp_und)
            logging.info("Parsed file {0}".format(fp_und))
        except:
            sys.exit("Failed to find or parse Undemultiplexed_stats.metrics")

    def _get_threshold_Q30(self):
        if self.demux_udfs.has_key('Threshold for % bases >= Q30'):
            self.Q30_treshold = self.demux_udfs['Threshold for % bases >= Q30']
            print >> self.qc_log_file, "THRESHOLD FOR %Q30 was set by user to {0}.".format(self.Q30_treshold)
        else:
            warning = "Un recognized read length: {0}. Report this to developers! set Threshold for % bases >= Q30 if you want to run bcl conversion and demultiplexing anyway.".format(self.read_length)
            if self.run_type == 'MiSeq':
                if self.read_length < 101:
                    Q30_threshold = 80
                elif self.read_length == 101:
                    Q30_threshold = 75
                elif self.read_length == 151:
                    Q30_threshold = 70
                elif self.read_length >= 251:
                    Q30_threshold = 60
                else:
                    sys.exit(warning)
            else:
                if self.read_length == 51:
                    Q30_threshold = 85
                elif self.read_length == 101:
                    Q30_threshold = 80
                elif self.read_length == 126:
                    Q30_threshold = 80
                elif self.read_length == 151:
                    Q30_threshold = 75
                else:
                    sys.exit(warning)
            print >> self.qc_log_file, "THRESHOLD FOR %Q30 was set to {0}. Value based on read length: {1}, and run type {2}.".format(
                               Q30_threshold, self.read_length, self.run_type)
            self.Q30_treshold = Q30_threshold

    def run_QC(self):
        ## dirty. needs clean up
        for pool in self.input_pools:
            outarts_per_lane = self.process.outputs_per_input(pool.id, ResultFile = True)
            LQC = LaneQC(pool, outarts_per_lane, self.run_type, self.undem_stat,
                     self.dem_stat, self.single,self.Q30_treshold)
            LQC.set_tresholds(self.qc_log_file, self.demux_udfs)
            LQC.lane_QC()
            self.nr_lane_samps_tot += LQC.nr_lane_samps
            self.nr_lane_samps_updat += LQC.nr_samps_updat
            if LQC.high_lane_yield:
                self.high_lane_yield.append(LQC.lane)
            if LQC.high_index_yield:
                self.high_index_yield.append(LQC.lane)

        ## moove this part to logging???-->>
        if self.high_index_yield or self.high_lane_yield:
            warn = "WARNING: "
            if self.high_index_yield:
                self.high_index_yield = ', '.join(list(set(self.high_index_yield)))
                warn = warn + "High yield of unexpected index on lane(s): {0} .".format(self.high_index_yield)
            if self.high_lane_yield:
                self.high_lane_yield = ', '.join(list(set(self.high_lane_yield)))
                warn = warn + "High total yield of unexpected index on lane(s): {0}.".format(self.high_lane_yield)
            warn = warn + "Please check the Metrics file!"
            self.abstract.insert(0, warn)

    def make_demultiplexed_counts_file(self, demuxfile):
        """Reformats the content of the demultiplex and undemultiplexed files
        to be more easy to read."""

        demuxfile = demuxfile + '.csv'
        keys = ['Project', 'Sample ID', 'Lane', '# Reads', 'Index',
                                    'Index name', '% of >= Q30 Bases (PF)']
        toCSV = []
        for pool in self.input_pools:
            if self.run_type == 'MiSeq':
                lane = '1'
            else:
                lane = pool.location[1][0]
            for row in self.dem_stat['Barcode_lane_statistics']:
                if row['Lane'] == lane:
                    row_dict = dict([(x, row[x]) for x in keys if x in row])
                    row_dict['Index name'] = ''
                    toCSV.append(row_dict)
            if lane in self.undem_stat.keys():
                undet_per_lane = self.undem_stat[lane]['undemultiplexed_barcodes']
                nr_undet = len(undet_per_lane['count'])
                for row in range(nr_undet):
                    row_dict = dict([(x, '') for x in keys])
                    row_dict['# Reads'] = undet_per_lane['count'][row]
                    row_dict['Index'] = undet_per_lane['sequence'][row]
                    row_dict['Index name'] = undet_per_lane['index_name'][row]
                    row_dict['Lane'] = undet_per_lane['lane'][row]
                    toCSV.append(row_dict)
        try:
            f = open(demuxfile, 'w')
            dict_writer = csv.DictWriter(f, keys, dialect='excel')
            dict_writer.writer.writerow(keys)
            dict_writer.writerows(toCSV)
            f.close
            self.abstract.append("INFO: A Metrics file has been created with "
                      "demultiplexed and undemultiplexed counts for debugging.")
        except:
            self.abstract.append("WARNING: Could not generate a Metrics file "
                               "with demultiplexed and undemultiplexed counts.")


    def logging(self):
        """Collects and prints logging info."""
        self.abstract.append("INFO: QC-data found and QC-flags uploaded for {0}"
              " out of {1} analytes.".format(self.nr_lane_samps_updat,
                                                        self.nr_lane_samps_tot))
        if self.QC_fail:
            self.abstract.append('Failed to make qc for samples: {0}'.format(
                ', '.join(self.QC_fail)))
        if 'WARNING' in ' '.join(self.abstract):
            sys.exit(' '.join(self.abstract))
        else:
            print >> sys.stderr, ' '.join(self.abstract)

    def make_qc_log_file(self, qc_log_file):
            self.qc_log_file = open(qc_log_file, 'a')



class LaneQC():
    def __init__(self, pool ,out_arts, run_type, undem_stat, dem_stat, single, Q30_treshold):
        self.single = single
        self.pool = pool
        self.out_arts = out_arts
        self.pool_udfs = dict(pool.udf.items()) ##will be used??
        self.run_type = run_type
        self.lane  = '1' if run_type == 'MiSeq' else pool.location[1][0]
        self.counts = undem_stat[self.lane]['undemultiplexed_barcodes']['count']
        self.nr_lane_samps = len(out_arts)
        self.reads_threshold = None #tres
        self.un_exp_lane = None #tres
        self.thres_un_exp_ind = None #tres
        self.Q30_treshold = Q30_treshold
        self.high_lane_yield = False
        self.high_index_yield = False
        self.BLS = dem_stat['Barcode_lane_statistics']
        self.nr_samps_updat = 0
        self.html_file_error = False

    def lane_QC(self):
        for target_file in self.out_arts:
            samp_name = target_file.samples[0].name
            for lane_samp in self.BLS:
                if self.lane == lane_samp['Lane']:
                    samp = lane_samp['Sample ID']
                    if samp == samp_name:
                        self._sample_fields(target_file, lane_samp)
                        try:
                            self._sample_QC(target_file, lane_samp)
                            set_field(target_file)
                            self.nr_samps_updat +=1 
                        except:
                            self.QC_fail.append(samp)
        self._check_un_exp_lane_yield()
        for index_count in self.counts:
            self._check_un_exp_ind_yield(index_count)

    def set_tresholds(self, qc_log_file, demux_udfs):
        print >> qc_log_file, ''
        print >> qc_log_file, 'TRESHOLDS - LANE {0}:'.format(self.lane)
        if self.run_type == 'MiSeq':
            if self.read_length in [76, 301]:   # ver3
                exp_lane_clust = 18000000
            else:                               # ver2
                exp_lane_clust = 10000000
        elif self.run_type == 'HiSeq Rapid Flow Cell v1':
            exp_lane_clust = 114000000
        elif self.run_type == 'HiSeq Flow Cell v3':
            exp_lane_clust = 143000000
        elif self.run_type == 'HiSeq Flow Cell v4':
            exp_lane_clust = 188000000
        elif self.run_type == 'HiSeqX10':
            exp_lane_clust = 250000000
        else:
            sys.exit('Unrecognized run type: {0}. Report to developer! Set '
                    'Threshold for # Reads if you want to run bcl conversion '
                    'and demultiplexing again'.format(self.run_type))
        if demux_udfs.has_key('Threshold for # Reads'):
            self.reads_threshold = demux_udfs['Threshold for # Reads']
            print >> qc_log_file , "Index yield - expected index: {0}".format(self.reads_threshold)
        else:
            exp_samp_clust = np.true_divide(exp_lane_clust, self.nr_lane_samps)
            self.reads_threshold = int(np.true_divide(exp_samp_clust, 2))
            print >> qc_log_file , "Index yield - expected index: {0}. Value based on nr of sampels in the lane: {1}, and run type {2}.".format(self.reads_threshold, self.nr_lane_samps, self.run_type)
        self.un_exp_lane = int(exp_lane_clust*0.05) if self.single else int(exp_lane_clust*0.1)
        print >> qc_log_file, 'Lane yield - un expected index: {0}. Value based on run type {1}, and run setings: {2}'.format(self.un_exp_lane, self.run_type, 'Single End' if self.single else 'Paired End')
        if demux_udfs.has_key('Threshold for Undemultiplexed Index Yield'):
            self.thres_un_exp_ind =  demux_udfs['Threshold for Undemultiplexed Index Yield']
            print >> qc_log_file, 'Index yield - un expected index: {0}. Value set by user.'.format(self.thres_un_exp_ind)
        else:
            self.thres_un_exp_ind = int(self.reads_threshold*0.1)
            print >> qc_log_file, 'Index yield - un expected index: {0}. Value set to 10% of expected index yield'.format(self.thres_un_exp_ind)



    def _sample_fields(self, t_file, stats):
        """ Populates the target file udfs. (run lane index resolution)
        stats -   Barcode lane statistics fetched from demultiplexed 
                        stats file
        t_file -   output artifact of the bcl-conv & demux process (run 
                        lane index resolution)"""
        samp_udfs = {'%PF' : stats['% PF'],
            '% One Mismatch Reads (Index)' : stats['% One Mismatch Reads (Index)'],
            '% of Raw Clusters Per Lane' : stats['% of raw clusters per lane'],
            'Ave Q Score' : stats['Mean Quality Score (PF)'],
            '% Perfect Index Read' : stats['% Perfect Index Reads']}

        for key, val in samp_udfs.items():
            try:
                t_file.udf[key] = float(val)
            except:
                self.html_file_error = True

        try:
            yMb = stats['Yield (Mbases)'].replace(',','')
            t_file.udf['Yield PF (Gb)'] = np.true_divide(float(yMb), 1000)
        except:
            self.html_file_error = True

        if not dict(t_file.udf.items()).has_key('% Bases >=Q30'):
            t_file.udf['% Bases >=Q30'] = stats['% of >= Q30 Bases (PF)']

        if not dict(t_file.udf.items()).has_key('# Reads'):
            try:
                nrr = float(stats['# Reads'].replace(',',''))
                t_file.udf['# Reads'] = nrr
            except:
                self.html_file_error = True

        if self.single and t_file.udf['# Reads']:
            t_file.udf['# Read Pairs'] = int(t_file.udf['# Reads'])
        elif t_file.udf['# Reads']:
            t_file.udf['# Read Pairs'] = np.true_divide(float(t_file.udf['# Reads']), 2)

    def _sample_QC(self, target_file, sample_info):
        """Makes per sample warnings if any of the following holds: 
                % Perfect Index Reads < ..
                % of >= Q30 Bases (PF) < ..
                # Reads < ..
            sets qc flaggs        
            Sets the include reads field
        OBS: Reads from target file udf if they are already set. Otherwise from 
        file system!!! This is to take into account yield and quality after 
        quality filtering if performed."""

        Q30 = float(sample_info['% of >= Q30 Bases (PF)'])
        QC2 = (Q30 >= self.Q30_treshold)
        QC3 = (target_file.udf['# Read Pairs'] >= self.reads_threshold)
        if QC2 and QC3:
            target_file.udf['Include reads'] = 'YES'
            target_file.qc_flag = 'PASSED'
        else:
            target_file.udf['Include reads'] = 'NO'
            target_file.qc_flag = 'FAILED'

    def _check_un_exp_lane_yield(self):
        unexp_lane_yield = sum([int(x) for x in self.counts])
        if unexp_lane_yield > self.un_exp_lane:
            self.high_lane_yield = True

    def _check_un_exp_ind_yield(self, index_count):    
        if int(index_count) > self.thres_un_exp_ind:
            self.high_index_yield = True

######################### 

def main(lims, pid, epp_logger, demuxfile, qc_log_file):
    process = Process(lims,id = pid)
    UDI = UndemuxInd(process)
    UDI.make_qc_log_file(qc_log_file)
    UDI.get_run_info()
    UDI.run_QC()
    UDI.make_demultiplexed_counts_file(demuxfile)
    UDI.logging()
    

if __name__ == "__main__":
    parser = ArgumentParser(description=DESC)
    parser.add_argument('--pid', default = None , dest = 'pid',
                        help='Lims id for current Process')
    parser.add_argument('--log', dest = 'log',
                        help=('File name for standard log file, '
                              'for runtime information and problems.'))
    parser.add_argument('--file', dest = 'file', default = 'demux',
                        help=('File path to demultiplexed metrics file'))
    parser.add_argument('--qc_log_file', dest = 'qc_log_file', default = 'qc_log_file',
                            help=('File path to qc logfile file'))
    args = parser.parse_args()
    lims = Lims(BASEURI, USERNAME, PASSWORD)
    lims.check_version()

    with EppLogger(log_file=args.log, lims=lims, prepend=True) as epp_logger:
        main(lims, args.pid, epp_logger, args.file, args.qc_log_file)
