
import os
import warnings


import numpy as np
import pandas as pd
import matplotlib.pyplot as plt


_HERE = os.path.dirname(__file__)
_TOFU_PATH = os.path.dirname(os.path.dirname(os.path.dirname(_HERE)))

# Import current tofu version
cwd = os.getcwd()
os.chdir(_TOFU_PATH)
import tofu as tf
os.chdir(_HERE)


# -----------------------------------------------------------------------------
#                   Default parameters
# -----------------------------------------------------------------------------


# _HERE = os.path.abspath(os.path.dirname(__file__))
_PFE = os.path.join(_HERE, 'WEST_Geometry_Rev_Nov2016_V2.xlsx')

# Toroidal width of a sector
_DTHETA = 2*np.pi / 18.

# 4 corners of a Casing Cover PJ from Creoview
_PJ_PTS = np.array([[313.728, -988.400, 2255.087],
                    [476.477, -988.400, 2226.390],
                    [313.728, -988.400, 1938.128],
                    [368.071, -988.400, 1928.547]])
_PJ_THETA = np.arctan2(_PJ_PTS[:, 2], _PJ_PTS[:, 0])
_PJ_DTHETA = np.abs(0.5*((_PJ_THETA[1]-_PJ_THETA[0])
                         + (_PJ_THETA[3]-_PJ_THETA[2])))
_PJ_POS0 = (0.5*((_PJ_THETA[1]+_PJ_THETA[0])/2 + (_PJ_THETA[3]+_PJ_THETA[2])/2)
            - _DTHETA)
_PJ_POS = (_PJ_POS0
           + np.r_[0, 1, 3, 4, 6, 7, 9, 10, 12, 13, 15, 16]*_DTHETA)
_CASING_DTHETA = [_DTHETA - _PJ_DTHETA, 2*_DTHETA - _PJ_DTHETA]
_CASING_POS = [_PJ_POS0 + _DTHETA/2 + np.arange(6)*3*_DTHETA,
               _PJ_POS0 + 2*_DTHETA + np.arange(6)*3*_DTHETA]
_CASING_DTHETA = np.tile(_CASING_DTHETA, 6)
_CASING_POS = np.array(_CASING_POS).T.ravel()


_EXP = 'WEST'
_DNAMES = {
    'Baffle': {
        'name': None,
    },
    'LPA': {
        'name': None,
    },
    'VDE': {
        'name': None,
    },
    # Vacuum vessels
    'Inner VV': {
        'name': 'InnerV0',
        'class': 'Ves',
        'save': True,
    },
    'Outer VV': {
        'name': 'OuterV0',
        'class': 'Ves',
        'save': True,
    },
    # Thermal shields
    'IVPP HFS': {
        'name': 'ThermalShieldHFSV0',
        'class': 'PFC',
        'thick': 0.008,
        'save': True,
    },
    'IVPP LFS': {
        'name': 'ThermalShieldLFSV0',
        'class': 'PFC',
        'thick': 0.008,
        'save': True,
    },
    # Lower divertor
    'LDiv PFUs': {
        'name': None,
    },
    'LDiv CasingCover': {
        'name': 'CasingCoverLDivV0',
        'class': 'PFC',
        'save': True,
    },
    'Ldiv Casing': {
        'name': 'CasingLDivV0',
        'class': 'PFC',
        'extent': _CASING_DTHETA,
        'pos': _CASING_POS,
        'save': True,
    },
    'Ldiv Casing PJ': {
        'name': 'CasingPJLDivV0',
        'class': 'PFC',
        'extent': _PJ_DTHETA,
        'pos': _PJ_POS,
        'save': True,
    },
    'Ldiv PFU Plate': {
        'name': 'CasingPFUPlateLDivV0',
        'class': 'PFC',
        'save': True,
    },
    # Upper divertor
    'UDiv PFUs': {
        'name': None,
    },
    'UDiv CasingCover': {
        'name': 'CasingCoverUDivV0',
        'class': 'PFC',
        'save': True,
    },
    'Udiv Casing': {
        'name': 'CasingUDivV0',
        'class': 'PFC',
        'extent': _CASING_DTHETA,
        'pos': _CASING_POS,
        'save': True,
    },
    'Udiv Casing PJ': {
        'name': 'CasingPJUDivV0',
        'class': 'PFC',
        'extent': _PJ_DTHETA,
        'pos': _PJ_POS,
        'save': True,
    },
    'Udiv PFU Plate': {
        'name': 'CasingPFUPlateUDivV0',
        'class': 'PFC',
        'save': True,
    },
}


# #############################################################################
# #############################################################################
#           Define PEI
# #############################################################################


def get_PEI():

    pts = np.array([
        [-1681.880, 555.372, 784.274],
        [-1670.349, 494.641, 778.897],
        [-1661.932, 444.534, 774.972],
        [-1652.797, 383.409, 770.712],
        [-1642.850, 303.089, 766.074],
        [-1635.270, 223.416, 762.539],
        [-1630.704, 155.868, 760.410],
        [-1627.334, 76.573, 758.838],
        [-1626.250, 2.920, 758.333],
        [-1627.273, -74.958, 758.810],
        [-1630.443, -151.695, 760.288],
        [-1635.199, -222.607, 762.506],
        [-1641.223, -288.671, 765.315],
        [-1649.738, -361.293, 769.285],
        [-1662.010, -445.008, 775.008],
        [-1670.139, -493.533, 778.799],
        [-1681.880, -555.372, 784.274],
    ])

    poly = 1.e-3*np.array([np.hypot(pts[:, 0], pts[:, 2]), pts[:, 1]])
    return poly


# #############################################################################
# #############################################################################
#           Extract and plot geometry
# #############################################################################


def get_all(
    pfe=None,
    dnames=None,
    ax=None,
    plot=None,
    save=None,
    return_ax=None,
):

    # --------------
    #   Plot
    if pfe is None:
        pfe = _PFE
    if dnames is None:
        dnames = _DNAMES
    if plot is None:
        plot = True
    if save is None:
        save = False
    if return_ax is None:
        return_ax = False

    # --------------
    #   Extract
    out = pd.read_excel(pfe, sheet_name='Main', header=[0, 1])

    ls = list(out.columns.levels[0])
    for ss in ls:
        nn = ss.split('\n')[0]
        if nn not in dnames.keys():
            continue
        poly = np.array([out[ss]['R (m)'], out[ss]['Z (m)']])
        if nn == 'IVPP HFS':
            poly = get_PEI()
        if 'thick' in dnames[nn].keys():
            dv = poly[:, 1:] - poly[:, :-1]
            vout = np.array([dv[1, :], -dv[0, :]])
            if nn == 'IVPP LFS' and np.nanmean(vout[0, :]) < 0:
                vout = -vout
            elif nn == 'IVPP HFS' and np.nanmean(vout[0, :]) > 0:
                vout = -vout
            vout = np.concatenate((vout[:, 0:1], vout), axis=1)
            vout = vout / np.sqrt(np.sum(vout**2, axis=0))[None, :]
            poly = np.concatenate(
                (poly,
                 poly[:, ::-1] + dnames[nn]['thick']*vout[:, ::-1]),
                axis=1
            )
        dnames[nn]['poly'] = poly
        indok = ~np.any(np.isnan(dnames[nn]['poly']), axis=0)
        if 'class' in dnames[nn].keys():
            try:
                dnames[nn]['obj'] = getattr(tf.geom, dnames[nn]['class'])(
                    Name=dnames[nn]['name'],
                    Poly=dnames[nn]['poly'][:, indok],
                    Exp=_EXP,
                    pos=dnames[nn].get('pos', None),
                    extent=dnames[nn].get('extent', None),
                )
            except Exception as err:
                msg = (str(err)
                       + "\ntofu object {} failed".format(nn))
                warnings.warn(str(err))

    # --------------
    #   Plot
    lobj = [nn for nn in dnames.keys() if dnames[nn].get('obj') is not None]
    if ax is None:
        if len(lobj) > 0:
            lax = None
            for oo in lobj:
                lax = dnames[oo]['obj'].plot(
                    lax=lax,
                    proj='all',
                    element='P',
                    indices=False,
                    dLeg=None,
                )
            ax = lax[0]
        else:
            fig = plt.figure(figsize=(10, 10))
            ax = fig.add_axes([0.1, 0.1, 0.8, 0.8], aspect='equal')

    for nn in dnames.keys():
        ll, = ax.plot(dnames[nn]['poly'][0, :], dnames[nn]['poly'][1, :],
                      label=nn)

    ax.legend(loc='upper left', bbox_to_anchor=(1., 1.))

    # --------------
    #   save
    if save is True:
        for nn in dnames.keys():
            c0 = (dnames[nn].get('save') is True
                  and dnames[nn].get('obj') is not None)
            if c0:
                dnames[nn]['obj'].save_to_txt(path=_HERE)

    if return_ax is True:
        return dnames, ax
    else:
        return dnames