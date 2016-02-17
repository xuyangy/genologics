"""Written by Isak Sylvin. isak.sylvin@scilifelab.se"""

import sys

class Thresholds():
    def __init__(self, instrument, chemistry, read_setup):
        self.valid_instruments = ['MiSeq', 'HiSeq', 'HiSeqX10']
        self.valid_chemistry = ['MiSeq', 'HiSeq Rapid Flow Cell v1','HiSeq Rapid Flow Cell v2', 
                             'TruSeq Rapid Flow Cell v2', 'TruSeq Rapid Flow Cell v3', 'HiSeq Flow Cell v4', 'HiSeqX10']
        self.valid_read_setups = ['Single','Mate-paired']
        
        self.Q30 = 0
        self.exp_lane_clust = 0
        
        #Check only valid values are entered
        if not instrument in self.valid_instruments or not chemistry in self.valid_chemistry or not read_setup in self.valid_read_setups:
            sys.exit("Detected instrument, chemistry and/or read_setup are not present in taca_bcl_thresholds.py")
        else:
            self.set_Q30(instrument, chemistry, read_setup)
            self.set_exp_lane_clust(instrument, chemistry, read_setup)
        
    def set_Q30(self, instrument, chemistry, read_setup):
        if instrument == 'MiSeq':
            if chemistry == 'MiSeq':
                if read_setup == 'Single':
                    self.Q30 = 75
        elif instrument == 'HiSeq':
            if chemistry in ['HiSeq Rapid Flow Cell v1','HiSeq Rapid Flow Cell v2', "TruSeq Rapid Flow Cell v2", "TruSeq Rapid Flow Cell v1"] :
                self.Q30 = 60
            elif chemistry == 'HiSeq Flow Cell v3':
                self.Q30 = 60
            elif chemistry == 'HiSeq Flow Cell v4':
                self.Q30 = 60
        elif instrument == 'HiSeqX10':
            self.Q30 = 50
    
    def set_exp_lane_clust(self, instrument, chemistry, read_setup):
        if instrument == 'MiSeq':
            if chemistry == 'MiSeq':
                if read_setup == 'Single':
                    self.exp_lane_clust = 10000000
        elif instrument == 'HiSeq':
            if chemistry in ['HiSeq Rapid Flow Cell v1','HiSeq Rapid Flow Cell v2', "TruSeq Rapid Flow Cell v2", "TruSeq Rapid Flow Cell v1"] :
                self.exp_lane_clust = 114000000
            elif chemistry == 'HiSeq Flow Cell v3':
               self.exp_lane_clust = 143000000
            elif chemistry == 'HiSeq Flow Cell v4':
                self.exp_lane_clust = 188000000
        elif instrument == 'HiSeqX10':
            self.exp_lane_clust = 250000000