import numpy as np
#from AllASPFuncs import find_parq, radec2point, SNID_to_loc

from AllASPFuncs import *

roman_path = '/hpc/group/cosmology/OpenUniverse2024'
sn_path = '/hpc/group/cosmology/OpenUniverse2024/roman_rubin_cats_v1.1.2_faint/'



def test_find_parq():
    parq_file_ID = find_parq(50134575, sn_path)
    assert parq_file_ID == 10430

def test_radec2point():
    p, s = radec2point(7.731890048839705, -44.4589649005717, 'Y106', path = roman_path)
    assert p == 10535
    assert s == 14

def test_SNID_to_loc():
    RA, DEC, p, s, start, end, peak, host_ra, host_dec = SNID_to_loc(50134575, 10430, 'Y106', date = True,\
     snpath = sn_path, roman_path = roman_path, host = True)
    assert RA == 7.731890048839705
    assert DEC ==  -44.4589649005717
    assert p == 10535
    assert s == 14
    assert start[0] == 62654.
    assert end[0] == 62958.
    assert peak[0] == np.float32(62683.98)
    assert host_ra == 7.731832
    assert host_dec == -44.459011


    
