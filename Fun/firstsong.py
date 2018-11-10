"""
This is the first song written for the keithley
"""
"""
rev
1/4/2011 - LNT - init
"""
import Keithley2400music
from time import sleep
keith=Keithley2400music.BasicGPIB()
tempo=120.0		# beats per minute
ts = 0.25		# quarter note gets the beat
# here are the notes used in the first song
C4 = 261.626
D4 = 293.665
E4 = 329.628
F4 = 349.228
G4 = 391.995
A4 = 440.000
B4 = 493.883
C5 = 523.251

"""
This is "Camp Down Races"
"""
############################################################
keith.e1(G4,tempo,ts)
keith.e1(G4,tempo,ts)
#
keith.e1(E4,tempo,ts)
keith.e1(G4,tempo,ts)
#
keith.e1(A4,tempo,ts)
keith.e1(G4,tempo,ts)
#
keith.q1(E4,tempo,ts)
#
############################################################
keith.e1(E4,tempo,ts)
keith.q1(D4,tempo,ts)
keith.eREST(tempo,ts)
#
keith.e1(E4,tempo,ts)
keith.q1(D4,tempo,ts)
keith.eREST(tempo,ts)
############################################################
keith.e1(G4,tempo,ts)
keith.e1(G4,tempo,ts)
#
keith.e1(E4,tempo,ts)
keith.e1(G4,tempo,ts)
#
keith.e1(A4,tempo,ts)
keith.e1(G4,tempo,ts)
#
keith.q1(E4,tempo,ts)
#
############################################################
keith.e1(D4,tempo,ts)

keith.s1(E4,tempo,ts)
keith.s1(F4,tempo,ts)
#
keith.e1(E4,tempo,ts)
keith.e1(D4,tempo,ts)
#
keith.h1(C4,tempo,ts)
#
#
############################################################
keith.e1(C4,tempo,ts)
#
keith.sREST(tempo,ts)
keith.s1(C4,tempo,ts)
#
keith.e1(E4,tempo,ts)
keith.e1(G4,tempo,ts)
#
keith.h1(C5,tempo,ts)
#
#
############################################################
keith.e1(A4,tempo,ts)
#
keith.sREST(tempo,ts)
keith.s1(A4,tempo,ts)
#
keith.e1(C5,tempo,ts)
keith.e1(A4,tempo,ts)
#
keith.q1(G4,tempo,ts)
keith.eREST(tempo,ts)
keith.s1(G4,tempo,ts)
keith.s1(G4,tempo,ts)
############################################################
keith.e1(G4,tempo,ts)
keith.e1(G4,tempo,ts)
#
keith.e1(E4,tempo,ts)
keith.e1(G4,tempo,ts)
#
keith.e1(A4,tempo,ts)
keith.e1(G4,tempo,ts)
#
keith.q1(E4,tempo,ts)
#
############################################################
keith.e1(D4,tempo,ts)

keith.s1(E4,tempo,ts)
keith.s1(F4,tempo,ts)
#
keith.e1(E4,tempo,ts)
keith.e1(D4,tempo,ts)
#
keith.h1(C4,tempo,ts)
#
#
