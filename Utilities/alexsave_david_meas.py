import numpy as np
class Preamp_Util():
    @staticmethod
    def init(self, instruments,
             set_preamp_gain=None,
             set_preamp_filter=None,
             set_preamp_dccouple=None,
             set_preamp_diffmode=None,
             ):

        self.preamp = instruments['preamp']
        self.set_preamp_gain = set_preamp_gain
        self.set_preamp_filter = set_preamp_filter
        self.set_preamp_dccouple = set_preamp_dccouple
        self.set_preamp_diffmode = set_preamp_diffmode
        Preamp_Util._setpreamp(self)
    
    @staticmethod
    def _setpreamp(self):
        if self.set_preamp_gain is not None:
            self.preamp.gain = self.set_preamp_gain
        if self.set_preamp_filter is not None:
            self.preamp.filter = self.set_preamp_filter
        if self.set_preamp_dccouple is not None:
            self.preamp.dc_coupling(self.set_preamp_dccouple)
        if self.set_preamp_diffmode is not None:
            self.preamp.diff_input(self.set_diffmode)

    @staticmethod
    def to_dict(self):
        return {'gain': self.preamp.gain,
                'filter': np.asarray(self.preamp.filter),
                'is_overloaded': int(self.preamp.is_OL()),
                'is_dccoupled': int(self.preamp.is_dc_coupled()),

                }
        #FIXME add dc coupling, diff mode
