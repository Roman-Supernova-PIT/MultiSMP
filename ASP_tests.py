from AllASPFuncs import *
from astropy.io import ascii
from astropy.utils.exceptions import AstropyWarning
from erfa import ErfaWarning
import galsim
import numpy as np
import os
import pandas as pd
import pathlib
from simulation import simulate_galaxy, simulate_images, simulate_supernova, \
                       simulate_wcs
import snappl
import tempfile
import warnings
import yaml

warnings.simplefilter('ignore', category=AstropyWarning)
warnings.filterwarnings("ignore", category=ErfaWarning)
roman_path = '/hpc/group/cosmology/OpenUniverse2024'
sn_path =\
     '/hpc/group/cosmology/OpenUniverse2024/roman_rubin_cats_v1.1.2_faint/'


def test_find_parquet():
    parq_file_ID = find_parquet(50134575, sn_path)
    assert parq_file_ID == 10430


def test_radec2point():
    p, s = radec2point(7.731890048839705, -44.4589649005717, 'Y106', path=roman_path)
    assert p == 10535
    assert s == 14


def test_get_object_info():
    ra, dec, p, s, start, end, peak  = get_object_info(50134575, 10430, 'Y106', \
     snpath = sn_path, roman_path = roman_path, obj_type = 'SN')
    assert ra == 7.731890048839705
    assert dec ==  -44.4589649005717
    assert p == 10535
    assert s == 14
    assert start[0] == 62654.
    assert end[0] == 62958.
    assert peak[0] == np.float32(62683.98)


def test_findAllExposures():
    explist = findAllExposures(50134575, 7.731890048839705, -44.4589649005717,62654.,62958.,62683.98, 'Y106', maxbg = 24, maxdet = 24, \
                        return_list = True, stampsize = 25, roman_path = roman_path,\
                    pointing_list = None, SCA_list = None, truth = 'simple_model')
    compare_table = ascii.read('tests/testdata/findallexposurestest.dat')
    assert explist['Pointing'].all() == compare_table['Pointing'].all()
    assert explist['SCA'].all() == compare_table['SCA'].all()
    assert explist['date'].all() == compare_table['date'].all()


def test_simulate_images():
    lam = 1293  # nm
    band = 'F184'
    airy = \
        galsim.ChromaticOpticalPSF(lam, diam=2.36, aberrations=galsim.roman.
                                   getPSF(1, band, pupil_bin=1).aberrations)
    # Fluxes for the simulated supernova, days arbitrary.
    test_lightcurve = [10, 100, 1000, 10**4, 10**5]
    images, im_wcs_list, cutout_wcs_list, sim_lc, util_ref = \
        simulate_images(num_total_images=10, num_detect_images=5, ra=7.541534306163982,
                        dec=-44.219205940734625,
                        sim_gal_ra_offset=1e-5,
                        sim_gal_dec_offset=1e-5, do_xshift=True,
                        do_rotation=True, sim_lc=test_lightcurve,

                        noise=0, use_roman=False, band='F184',
                        deltafcn_profile=False, roman_path=roman_path, size=11,
                        input_psf=airy, bg_gal_flux=9e5)

    compare_images = np.load('tests/testdata/images.npy')
    assert compare_images.all() == np.asarray(images).all()


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
    wcs_data = np.load('./tests/testdata/wcs_dict.npz', allow_pickle=True)
    # Loading the data in this way, the data is packaged in an array,
    # this extracts just the value so that we can build the WCS.
    wcs_dict = {key: wcs_data[key].item() for key in wcs_data.files}

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

    print(supernova_image.flatten()[:10])
    b = np.load('./tests/testdata/supernova_image.npy')
    print(b.flatten()[:10])
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


def test_run_on_star():
    config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                               'config.yaml')
    config = yaml.safe_load(open(config_path))
    config['grid_type'] = 'none'

    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False)\
            as temp_config:
        yaml.dump(config, temp_config)
        temp_config_path = temp_config.name

    err_code = os.system(f'python RomanASP.py -s 40973149150 -f Y106 -t 1 -d 1\
                          -o "tests/testdata" --config {temp_config_path}\
                          --object_type star')
    assert err_code == 0, "The test run on a star failed. Check the logs"


def test_regression():
    # Regression lightcurve was changed on 5.29.2025 to fix an off by one err.
    config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                               'config.yaml')
    config = yaml.safe_load(open(config_path))
    config['use_roman'] = True
    config['use_real_images'] = True
    config['fetch_SED'] = False
    config['grid_type'] = 'contour'
    config['band'] = 'Y106'
    config['size'] = 19
    config['weighting'] = True
    config['subtract_background'] = True
    # Weighting is a Gaussian width 1000 when this was made
    # In the future, this should be True, but random seeds not working rn.
    config['source_phot_ops'] = False

    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False)\
            as temp_config:
        yaml.dump(config, temp_config)
        temp_config_path = temp_config.name
    output = os.system(f'python RomanASP.py -s 40120913 -f Y106 -t 2 -d 1 -o \
              "tests/testdata" --config {temp_config_path}')
    assert output == 0, "The test run on a SN failed. Check the logs"

    current = pd.read_csv('tests/testdata/40120913_Y106_romanpsf_lc.ecsv',
                          comment='#', delimiter=' ')
    comparison = pd.read_csv('tests/testdata/test_lc.ecsv', comment='#',
                              delimiter=' ')

    for col in current.columns:
        # According to Michael and Rob, this is roughly what can be expected
        # due to floating point precision.
        msg = "The lightcurves do not match for column %s" % col
        if col == 'band':
            # band is the only string column, so we check it with array_equal
            np.testing.assert_array_equal(current[col], comparison[col]), msg
        else:
            percent = 100 * np.max((current[col] - comparison[col]) / comparison[col])
            msg2 = f"difference is {percent} %"
            msg = msg+msg2
            np.testing.assert_allclose(current[col], comparison[col], rtol=1e-7), msg


def test_get_galsim_SED():
    sed = get_galsim_SED(40973149150, 000, sn_path, obj_type='star',
                                  fetch_SED=True)
    lam = sed._spec.x
    flambda = sed._spec.f
    assert np.array_equal(lam, np.load('./tests/testdata/star_lam_test.npy')),\
        "The wavelengths do not match the star test example"
    assert np.array_equal(flambda,
                          np.load('./tests/testdata/star_flambda_test.npy')),\
        "The fluxes do not match the star test example"

    sed = get_galsim_SED(40120913, 62535.424, sn_path, obj_type='SN',
                                  fetch_SED=True)
    lam = sed._spec.x
    flambda = sed._spec.f
    assert np.array_equal(lam, np.load('./tests/testdata/sn_lam_test.npy')), \
        "The wavelengths do not match the SN test example"
    assert np.array_equal(flambda,
                          np.load('./tests/testdata/sn_flambda_test.npy')), \
        "The fluxes do not match the SN test example"


def test_get_galsim_SED_list():
    exposures = {'date': [62535.424], 'DETECTED': [True]}
    exposures = pd.DataFrame(exposures)
    fetch_SED = True
    object_type = 'SN'
    ID = 40120913
    sedlist = get_galsim_SED_list(ID, exposures, fetch_SED, object_type, sn_path)
    assert len(sedlist) == 1, "The length of the SED list is not 1"
    assert np.array_equal(sedlist[0]._spec.x,
                          np.load('./tests/testdata/sn_lam_test.npy')), \
        "The wavelengths do not match the SN test example"
    assert np.array_equal(sedlist[0]._spec.f,
                          np.load('./tests/testdata/sn_flambda_test.npy')), \
        "The fluxes do not match the SN test example"


def test_plot_lc():
    from AllASPFuncs import plot_lc
    output = plot_lc('./tests/testdata/test_lc_plot.ecsv', return_data=True)
    assert output[0][0] == 23.34624211038908
    assert output[1][0] == 62535.424
    assert output[2][0] == 0.3464661982648008
    assert output[3][0] == 23.164154309471726
    assert output[4] == 182.088
    assert output[5] == 0.0


def test_extract_sn_from_parquet_file_and_write_to_csv():
    output_path = pathlib.Path(__file__).parent/"tests/testdata/snids.csv"
    extract_sn_from_parquet_file_and_write_to_csv(10430, sn_path,
                                                  output_path,
                                                  mag_limits=[20, 21])
    sn_ids = pd.read_csv(output_path, header=None).values.flatten()
    test_sn_ids = pd.read_csv(pathlib.Path(__file__).parent/"tests/testdata/test_snids.csv", header=None).values.flatten()
    assert np.array_equal(sn_ids, test_sn_ids), "The SNIDs do not match the test example"


def test_make_regular_grid():
    wcs_data = np.load('./tests/testdata/wcs_dict.npz', allow_pickle=True)
    # Loading the data in this way, the data is packaged in an array,
    # this extracts just the value so that we can build the WCS.
    wcs_dict = {key: wcs_data[key].item() for key in wcs_data.files}
    ra_center = wcs_dict['CRVAL1']
    dec_center = wcs_dict['CRVAL2']

    test_ra = np.array([7.67363133, 7.67373506, 7.67383878, 7.67355803,
                        7.67366176, 7.67376548, 7.67348473, 7.67358845,
                        7.67369218])
    test_dec = np.array([-44.26396874, -44.26391831, -44.26386787,
                        -44.26389673, -44.26384629, -44.26379586,
                        -44.26382471, -44.26377428, -44.26372384])
    for wcs in [snappl.wcs.GalsimWCS.from_header(wcs_dict),
                snappl.wcs.AstropyWCS.from_header(wcs_dict)]:
        ra_grid, dec_grid = make_regular_grid(ra_center, dec_center, wcs,
                                              size=25, spacing=3.0)
        np.testing.assert_allclose(ra_grid, test_ra, atol=1e-9), \
            "RA vals do not match"
        np.testing.assert_allclose(dec_grid, test_dec, atol=1e-9), \
            "Dec vals do not match"


def test_make_adaptive_grid():
    wcs_data = np.load('./tests/testdata/wcs_dict.npz', allow_pickle=True)
    # Loading the data in this way, the data is packaged in an array,
    # this extracts just the value so that we can build the WCS.
    wcs_dict = {key: wcs_data[key].item() for key in wcs_data.files}
    ra_center = wcs_dict['CRVAL1']
    dec_center = wcs_dict['CRVAL2']
    for wcs in [snappl.wcs.GalsimWCS.from_header(wcs_dict),
                snappl.wcs.AstropyWCS.from_header(wcs_dict)]:
        compare_images = np.load('tests/testdata/images.npy')
        image = compare_images[:11**2].reshape(11, 11)
        ra_grid, dec_grid = make_adaptive_grid(ra_center, dec_center, wcs,
                                               image=image, percentiles=[99])
        test_ra = [7.67356034, 7.67359491, 7.67362949, 7.67366407, 7.67369864,]
        test_dec = [-44.26425446, -44.26423765, -44.26422084, -44.26420403,
                    -44.26418721]
        # Only testing the first 5 to save memory.
        np.testing.assert_allclose(ra_grid[:5], test_ra, atol=1e-9), \
            "RA vals do not match"
        np.testing.assert_allclose(dec_grid[:5], test_dec, atol=1e-9), \
            "Dec vals do not match"


def test_make_contour_grid():
    wcs_data = np.load('./tests/testdata/wcs_dict.npz', allow_pickle=True)
    # Loading the data in this way, the data is packaged in an array,
    # this extracts just the value so that we can build the WCS.
    wcs_dict = {key: wcs_data[key].item() for key in wcs_data.files}
    test_ra = [7.67357048, 7.67360506, 7.67363963, 7.67367421]
    test_dec = [-44.26421364, -44.26419683, -44.26418002, -44.26416321]
    atol = 1e-9
    for wcs in [snappl.wcs.GalsimWCS.from_header(wcs_dict),
                snappl.wcs.AstropyWCS.from_header(wcs_dict)]:
        compare_images = np.load('tests/testdata/images.npy')
        image = compare_images[:11**2].reshape(11, 11)
        ra_grid, dec_grid = make_contour_grid(image, wcs)
        msg = f"RA vals do not match to {atol:.1e} using galsim wcs."
        np.testing.assert_allclose(ra_grid[:4], test_ra, atol=atol, rtol=1e-9), msg
        msg = f"Dec vals do not match to {atol:.1e} using galsim wcs."
        np.testing.assert_allclose(dec_grid[:4], test_dec, atol=atol, rtol=1e-9), msg


def test_calculate_background_level():
    from AllASPFuncs import calculate_background_level
    test_data = np.ones((12, 12))
    test_data[5:7, 5:7] = 1000

    # Add some outliers to prevent all of
    # the data from being sigma clipped.
    test_data[0:2, 0:12:2] = 123
    test_data[-3:-1, 0:12:2] = 123
    test_data[0:12:2, 0:2] = 123
    test_data[0:12:2, -1:-3] = 123

    expected_output = 1
    output = calculate_background_level(test_data)
    msg = f"Expected {expected_output}, but got {output}"
    assert np.isclose(output, expected_output, rtol=1e-7), msg


def test_calc_mag_and_err():
    flux = np.array([-1e2, 1e2, 1e3, 1e4])
    sigma_flux = np.array([10, 10, 10, 10])
    band = 'Y106'
    mag, magerr, zp = calc_mag_and_err(flux, sigma_flux, band)

    test_mag = np.array([np.nan, 27.66165575,  25.16165575,  22.66165575])
    test_magerr = np.array([np.nan, 1.0857362e-01,
                            1.0857362e-02, 1.0857362e-03])
    test_zp = 15.023547191066587

    np.testing.assert_allclose(mag, test_mag, atol=1e-7, equal_nan=True), \
         f"The magnitudes do not match {mag} VS. {test_mag}"
    np.testing.assert_allclose(magerr, test_magerr, atol=1e-7, equal_nan=True), \
         "The magnitude errors do not match"
    np.testing.assert_allclose(zp, test_zp, atol=1e-7), "The zeropoint does not match"

