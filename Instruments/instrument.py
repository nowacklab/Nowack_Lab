'''
For the future? Instrument base class that all instruments belong to.
'''
class Instrument:
    _label = 'instrument'

    def __getstate__(self):
    	return self.__dict__

    def __setstate__(self, state):
    	'''
    	Setstate for an instrument by default does not load an instrument.
    	You must custom-write setstates if you want private variables to be loaded.
    	It is not recommended to load directly into properties, in case this makes
    	an unwanted change to the physical instrument.
    	'''
    	pass