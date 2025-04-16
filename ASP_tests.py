import numpy as np
import galsim
import warnings
from simulation import simulate_images, simulate_galaxy, simulate_wcs, \
     simulate_supernova
from AllASPFuncs import *
from astropy.io import ascii
from astropy.utils.exceptions import AstropyWarning
from erfa import ErfaWarning
warnings.simplefilter('ignore', category=AstropyWarning)
warnings.filterwarnings("ignore", category=ErfaWarning)
roman_path = '/hpc/group/cosmology/OpenUniverse2024'
sn_path =\
     '/hpc/group/cosmology/OpenUniverse2024/roman_rubin_cats_v1.1.2_faint/'


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


def test_findAllExposures():
    explist = findAllExposures(50134575, 7.731890048839705, -44.4589649005717,62654.,62958.,62683.98, 'Y106', maxbg = 24, maxdet = 24, \
                        return_list = True, stampsize = 25, roman_path = roman_path,\
                    pointing_list = None, SCA_list = None, truth = 'simple_model')
    compare_table = ascii.read('tests/testdata/findallexposurestest.dat')
    assert explist['Pointing'].all() == compare_table['Pointing'].all()
    assert explist['SCA'].all() == compare_table['SCA'].all()
    assert explist['date'].all() == compare_table['date'].all()


def test_simulate_images():
    band = 'F184'
    lam = 1293  # nm
    airy = \
        galsim.ChromaticOpticalPSF(lam, diam=2.36, aberrations=galsim.roman.
                                   getPSF(1, band, pupil_bin=1).aberrations)
    images, im_wcs_list, cutout_wcs_list, psf_storage, sn_storage = \
        simulate_images(testnum=10, detim=5, ra=7.541534306163982,
                        dec=-44.219205940734625, do_xshift=True,
                        do_rotation=True, supernova=[10, 100, 1000,
                                                     10**4, 10**5],
                        noise=0, use_roman=False, band='F184',
                        deltafcn_profile=False, roman_path=roman_path, size=11,
                        input_psf=airy, bg_gal_flux=9e5)
    compare_images = np.load('tests/testdata/images.npy')
    assert compare_images.all() == images.all()


def test_simulate_wcs():
    wcs_dict = simulate_wcs(angle=np.pi/4, x_shift=0.1, y_shift=0,
                            roman_path=roman_path, base_sca=11,
                            base_pointing=662, band='F184')
    b = np.load('./tests/testdata/wcs_dict.npz', allow_pickle=True)
    assert wcs_dict == b, 'WCS simulation does not match test example'


def test_simulate_galaxy():
    band = 'F184'
    roman_bandpasses = galsim.roman.getBandpasses()
    lam = 1293  # nm
    sed = galsim.SED(galsim.LookupTable([100, 2600], [1, 1],
                     interpolant='linear'), wave_type='nm',
                     flux_type='fphotons')
    sim_psf = \
        galsim.ChromaticOpticalPSF(lam, diam=2.36, aberrations=galsim.roman.
                                   getPSF(1, band, pupil_bin=1).aberrations)
    convolved = simulate_galaxy(bg_gal_flux=9e5, deltafcn_profile=False,
                                band=band, sim_psf=sim_psf, sed=sed)

    a = convolved.drawImage(roman_bandpasses[band], method='no_pixel',
                            use_true_center=True)
    b = np.load('./tests/testdata/test_galaxy.npy')
    assert (a.array - b).all() == 0, "The two galaxy images are not the same!"


def test_simulate_supernova():
    wcs_dict = np.load('./tests/testdata/wcs_dict.npz', allow_pickle=True)

    wcs_dict = dict(wcs_dict)
    for key in wcs_dict.keys():
        wcs_dict[key] = wcs_dict[key].item()

    wcs, origin = galsim.wcs.readFromFitsHeader(wcs_dict)

    stamp = galsim.Image(11, 11, wcs=wcs)
    band = 'F184'
    lam = 1293  # nm
    sed = galsim.SED(galsim.LookupTable([100, 2600], [1, 1],
                     interpolant='linear'), wave_type='nm',
                     flux_type='fphotons')
    sim_psf = \
        galsim.ChromaticOpticalPSF(lam, diam=2.36, aberrations=galsim.roman.
                                   getPSF(1, band, pupil_bin=1).aberrations)
    supernova_image = simulate_supernova(snx=6, sny=6, stamp=stamp,
                                         flux=1000, sed=sed, band=band,
                                         sim_psf=sim_psf, source_phot_ops=True,
                                         base_pointing=662, base_sca=11,
                                         random_seed=12345)
    b = np.load('./tests/testdata/supernova_image.npy')
    assert (supernova_image - b).all() == 0, 'Test SN image does not \
    match expected output.'


def test_savelightcurve():
    data_dict = {'MJD': [1,2,3,4,5], 'true_flux': [1,2,3,4,5], 'measured_flux': [1,2,3,4,5]}
    units = {'MJD':u.d, 'true_flux': '',  'measured_flux': ''}
    meta_dict = {}
    lc = QTable(data = data_dict, meta = meta_dict, units = units)
    save_lightcurve(lc, 'test', 'test', 'test')

    output_path = os.path.join(os.getcwd(), 'results/lightcurves/')
    lc_file = os.path.join(output_path, 'test_test_test_lc.ecsv')
    assert os.path.exists(lc_file) == True

