"""Written by Isak Sylvin. isak.sylvin@scilifelab.se"""

import sys

class Thresholds():
    def __init__(self, instrument, chemistry, paired):
        self.valid_instruments = ['MiSeq', 'HiSeq', 'HiSeqX10']
        self.valid_chemistry = ['MiSeq', 'HiSeq Rapid Flow Cell v1','HiSeq Rapid Flow Cell v2', 
                             'TruSeq Rapid Flow Cell v2', 'TruSeq Rapid Flow Cell v3', 'HiSeq Flow Cell v4', 'HiSeqX10']
        
        self.Q30 = 0
        self.exp_lane_clust = 0
        
        #Check only valid values are entered
        if not instrument in self.valid_instruments or not chemistry in self.valid_chemistry:
            sys.exit("Detected instrument, chemistry and/or read_setup are not present in bcl_thresholds.py")
        else:
            self.set_Q30(instrument, chemistry, paired)
            self.set_exp_lane_clust(instrument, chemistry, paired)
    
    #Q30 values here go for max read length
    #If read length should be a factor, values need to be upd.
    def set_Q30(self, instrument, chemistry, paired):
        if instrument == 'MiSeq':
            if chemistry == 'MiSeq':
                if not paired:
                    self.Q30 = 60
        elif instrument == 'HiSeq':
            if chemistry in ['HiSeq Rapid Flow Cell v1','HiSeq Rapid Flow Cell v2', "TruSeq Rapid Flow Cell v2", "TruSeq Rapid Flow Cell v1"] :
                self.Q30 = 75
            elif chemistry == 'HiSeq Flow Cell v3':
                self.Q30 = 80
            elif chemistry == 'HiSeq Flow Cell v4':
                self.Q30 = 80
        elif instrument == 'HiSeqX10':
            self.Q30 = 75
    
    def set_exp_lane_clust(self, instrument, chemistry, paired):
        if instrument == 'MiSeq':
            if chemistry == 'MiSeq':
                if not paired:
                    self.exp_lane_clust = 18000000
        elif instrument == 'HiSeq':
            if chemistry in ['HiSeq Rapid Flow Cell v1','HiSeq Rapid Flow Cell v2', "TruSeq Rapid Flow Cell v2", "TruSeq Rapid Flow Cell v1"] :
                self.exp_lane_clust = 114000000
            elif chemistry == 'HiSeq Flow Cell v3':
               self.exp_lane_clust = 143000000
            elif chemistry == 'HiSeq Flow Cell v4':
                self.exp_lane_clust = 188000000
        elif instrument == 'HiSeqX10':
            self.exp_lane_clust = 250000000