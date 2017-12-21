

class ilgate(Measurement):

    def __init__(self, zurich, dcbias, idc, acsignal, iac):
        '''
        Initializes a ilgate object. IL gate must be controlled by a single
        zurich lock in amplifier. dcbias, idc, acsignal, iac shoud be the names
        of the properties corresponding to the dc voltage on the gate, the dc
        current through the gate, 
