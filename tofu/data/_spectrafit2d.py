
# Built-in
import os
import warnings
import itertools as itt
import copy
import datetime as dtm      # DB

# Common
import numpy as np
import scipy.optimize as scpopt
import scipy.constants as scpct
import scipy.sparse as sparse
from scipy.interpolate import BSpline
import matplotlib.pyplot as plt


#                   --------------
#       TO BE MOVED TO tofu.data WHEN FINISHED !!!!
#                   --------------


_NPEAKMAX = 12
_DCONSTRAINTS = {'amp': False,
                 'width': False,
                 'shift': False,
                 'double': False}


###########################################################
###########################################################
#
#           Preliminary
#       utility tools for 1d spectral fitting
#
###########################################################
###########################################################


def remove_bck(x, y):
    # opt = np.polyfit(x, y, deg=0)
    opt = [np.nanmin(y)]
    return y-opt[0], opt[0]


def get_peaks(x, y, nmax=None):

    if nmax is None:
        nmax = _NPEAKMAX

    # Prepare
    ybis = np.copy(y)
    A = np.empty((nmax,), dtype=y.dtype)
    x0 = np.empty((nmax,), dtype=x.dtype)
    sigma = np.empty((nmax,), dtype=y.dtype)
    def gauss(xx, A, x0, sigma): return A*np.exp(-(xx-x0)**2/sigma**2)
    def gauss_jac(xx, A, x0, sigma):
        jac = np.empty((xx.size, 3), dtype=float)
        jac[:, 0] = np.exp(-(xx-x0)**2/sigma**2)
        jac[:, 1] = A*2*(xx-x0)/sigma**2 * np.exp(-(xx-x0)**2/sigma**2)
        jac[:, 2] = A*2*(xx-x0)**2/sigma**3 * np.exp(-(xx-x0)**2/sigma**2)
        return jac

    dx = np.nanmin(np.diff(x))

    # Loop
    nn = 0
    while nn < nmax:
        ind = np.nanargmax(ybis)
        x00 = x[ind]
        if np.any(np.diff(ybis[ind:], n=2) >= 0.):
            wp = min(x.size-1,
                     ind + np.nonzero(np.diff(ybis[ind:],n=2)>=0.)[0][0] + 1)
        else:
            wp = ybis.size-1
        if np.any(np.diff(ybis[:ind+1], n=2) >= 0.):
            wn = max(0, np.nonzero(np.diff(ybis[:ind+1],n=2)>=0.)[0][-1] - 1)
        else:
            wn = 0
        width = x[wp]-x[wn]
        assert width>0.
        indl = np.arange(wn, wp+1)
        sig = np.ones((indl.size,))
        if (np.abs(np.mean(np.diff(ybis[ind:wp+1])))
            > np.abs(np.mean(np.diff(ybis[wn:ind+1])))):
            sig[indl < ind] = 1.5
            sig[indl > ind] = 0.5
        else:
            sig[indl < ind] = 0.5
            sig[indl > ind] = 1.5
        p0 = (ybis[ind], x00, width)#,0.)
        bounds = (np.r_[0., x[wn], dx/2.],
                  np.r_[5.*ybis[ind], x[wp], 5.*width])
        try:
            (Ai, x0i, sigi) = scpopt.curve_fit(gauss, x[indl], ybis[indl],
                                               p0=p0, bounds=bounds, jac=gauss_jac,
                                               sigma=sig, x_scale='jac')[0]
        except Exception as err:
            print(str(err))
            import ipdb
            ipdb.set_trace()
            pass

        ybis = ybis - gauss(x, Ai, x0i, sigi)
        A[nn] = Ai
        x0[nn] = x0i
        sigma[nn] = sigi


        nn += 1
    return A, x0, sigma

def get_p0bounds_all(x, y, nmax=None, lamb0=None):

    yflat, bck = remove_bck(x, y)
    amp, x0, sigma = get_peaks(x, yflat, nmax=nmax)
    lamb0 = x0
    nmax = lamb0.size

    p0 = amp.tolist() + [0 for ii in range(nmax)] + sigma.tolist() + [bck]

    lx = [np.nanmin(x), np.nanmax(x)]
    Dx = np.diff(lx)
    dx = np.nanmin(np.diff(x))

    bamp = (np.zeros(nmax,), np.full((nmax,),3.*np.nanmax(y)))
    bdlamb = (np.full((nmax,), -Dx/2.), np.full((nmax,), Dx/2.))
    bsigma = (np.full((nmax,), dx/2.), np.full((nmax,), Dx/2.))
    bbck0 = (0., np.nanmax(y))

    bounds = (np.r_[bamp[0], bdlamb[0], bsigma[0], bbck0[0]],
              np.r_[bamp[1], bdlamb[1], bsigma[1], bbck0[1]])
    if not np.all(bounds[0]<bounds[1]):
        msg = "Lower bounds must be < upper bounds !\n"
        msg += "    lower :  %s\n"+str(bounds[0])
        msg += "    upper :  %s\n"+str(bounds[1])
        raise Exception(msg)
    return p0, bounds, lamb0

def get_p0bounds_lambfix(x, y, nmax=None, lamb0=None):

    nmax = lamb0.size
    # get typical x units
    Dx = x.nanmax()-x.nanmin()
    dx = np.nanmin(np.diff(x))

    # Get background and background-subtracted y
    yflat, bck = remove_bck(x, y)

    # get initial guesses
    amp = [yflat[np.nanargmin(np.abs(x-lamb))] for lamb in lamb0]
    sigma = [Dx/nmax for ii in range(nmax)]
    p0 = A + sigma + [bck]

    # Get bounding boxes
    bamp = (np.zeros(nmax,), np.full((nmax,),3.*np.nanmax(y)))
    bsigma = (np.full((nmax,), dx/2.), np.full((nmax,), Dx/2.))
    bbck0 = (0., np.nanmax(y))

    bounds = (np.r_[bamp[0], bsigma[0], bbck0[0]],
              np.r_[bamp[1], bsigma[1], bbck0[1]])
    if not np.all(bounds[0]<bounds[1]):
        msg = "Lower bounds must be < upper bounds !\n"
        msg += "    lower :  %s\n"+str(bounds[0])
        msg += "    upper :  %s\n"+str(bounds[1])
        raise Exception(msg)
    return p0, bounds, lamb0


def get_func1d_all(n=5, lamb0=None):
    if lamb0 is None:
        lamb0 = np.zeros((n,), dtype=float)
    assert lamb0.size == n

    def func_vect(x, amp, dlamp, sigma, bck0, lamb0=lamb0, n=n):
        y = np.full((n+1, x.size), np.nan)
        y[:-1, :] = amp[:, None]*np.exp(-(x[None, :]-(lamb0+dlamb)[:, None])**2
                                        /sigma[:, None]**2)
        y[-1, :] = bck0
        return y

    def func_sca(x, *args, lamb0=lamb0, n=n):
        amp = np.r_[args[0:n]][:, None]
        dlamb = np.r_[args[n:2*n]][:, None]
        sigma = np.r_[args[2*n:3*n]][:, None]
        bck0 = np.r_[args[3*n]]
        gaus = amp * np.exp(-(x[None, :]-(lamb0[:, None] + dlamb))**2/sigma**2)
        back = bck0
        return np.sum(gaus, axis=0) + back

    def func_sca_jac(x, *args, lamb0=lamb0, n=n):
        amp = np.r_[args[0:n]][None, :]
        dlamb = np.r_[args[n:2*n]][None, :]
        sigma = np.r_[args[2*n:3*n]][None, :]
        bck0 = np.r_[args[3*n]]
        lamb0 = lamb0[None, :]
        x = x[:, None]
        jac = np.full((x.size, 3*n+1,), np.nan)
        jac[:, :n] = np.exp(-(x - (lamb0+dlamb))**2/sigma**2)
        jac[:, n:2*n] = amp*2*((x - (lamb0+dlamb))/(sigma**2)
                               * np.exp(-(x - (lamb0+dlamb))**2/sigma**2))
        jac[:, 2*n:3*n] = amp*2*((x - (lamb0+dlamb))**2/sigma**3
                                 * np.exp(-(x - (lamb0+dlamb))**2/sigma**2))
        jac[:, -1] = 1.
        return jac

    return func_vect, func_sca, func_sca_jac


def get_func1d_lamb0fix(n=5, lamb0=None):
    if lamb0 is None:
        lamb0 = np.zeros((n,), dtype=float)
    assert lamb0.size == n

    def func_vect(x, amp, sigma, bck0, lamb0=lamb0, n=n):
        y = np.full((n+1, x.size), np.nan)
        for ii in range(n):
            y[ii, :] = amp[ii]*np.exp(-(x-lamb0[ii])**2/sigma[ii]**2)
        y[-1, :] = bck0
        return y

    def func_sca(x, *args, lamb0=lamb0, n=n):
        amp = np.r_[args[0:n]][:, None]
        sigma = np.r_[args[2*n:3*n]][:, None]
        bck0 = np.r_[args[3*n]]
        gaus = amp * np.exp(-(x[None, :]-lamb0[:, None])**2/sigma**2)
        back = bck0
        return np.sum(gaus, axis=0) + back

    def func_sca_jac(x, *args, lamb0=lamb0, n=n):
        amp = np.r_[args[0:n]][None, :]
        sigma = np.r_[args[2*n:3*n]][None, :]
        bck0 = np.r_[args[3*n]]
        lamb0 = lamb0[None, :]
        x = x[:, None]
        jac = np.full((x.size, 2*n+1,), np.nan)
        jac[:, :n] = np.exp(-(x - lamb0)**2/sigma**2)
        jac[:, n:2*n] = amp*2*((x - lamb0)**2/sigma**3
                                 * np.exp(-(x-lamb0)**2/sigma**2))
        jac[:, -1] = 1.
        return jac

    return func_vect, func_sca, func_sca_jac


def multiplegaussianfit1d(x, spectra, nmax=None,
                          lamb0=None, forcelamb=None,
                          p0=None, bounds=None,
                          max_nfev=None, xtol=None, verbose=0,
                          percent=None, plot_debug=False):
    # Check inputs
    if xtol is None:
        xtol = 1.e-8
    if percent is None:
        percent = 20


    # Prepare
    if spectra.ndim == 1:
        spectra = spectra.reshape((1,spectra.size))
    nt = spectra.shape[0]

    # Prepare info
    if verbose is not None:
        print("----- Fitting spectra with {0} gaussians -----".format(nmax))
    nspect = spectra.shape[0]
    nstr = max(nspect//max(int(100/percent), 1), 1)

    # get initial guess function
    if forcelamb is True:
        get_p0bounds = get_p0bounds_lambfix
    else:
        get_p0bounds = get_p0bounds_all

    # lamb0
    if p0 is None or bounds is None or lamb0 is None:
        p00, bounds0, lamb00 = get_p0bounds_all(x, spectra[0,:],
                                              nmax=nmax, lamb0=lamb0)
        if lamb0 is None:
            lamb0 = lamb00
        assert lamb0 is not None
        if forcelamb is True:
            p00 = p00[:nmax] + p00[2*nmax:]
            bounds0 = bounds0[:nmax] + bounds0[2*nmax:]
        if p0 is None:
            p0 = p00
        if bounds is None:
            bounds = bounds0
    if nmax is None:
        nmax = lamb0.size
    assert nmax == lamb0.size

    # Get fit vector, scalar and jacobian functions
    if forcelamb is True:
        func_vect, func_sca, func_sca_jac = get_func1d_lambfix(n=nmax,
                                                               lamb0=lamb0)
    else:
        func_vect, func_sca, func_sca_jac = get_func1d_all(n=nmax,
                                                           lamb0=lamb0)

    # Prepare index for splitting p0
    if forcelamb is True:
        indsplit = nmax*np.r_[1, 2]
    else:
        indsplit = nmax*np.r_[1, 2, 3]

    # Prepare output
    fit = np.full(spectra.shape, np.nan)
    amp = np.full((nt, nmax), np.nan)
    sigma = np.full((nt, nmax), np.nan)
    bck = np.full((nt,), np.nan)
    ampstd = np.full((nt, nmax), np.nan)
    sigmastd = np.full((nt, nmax), np.nan)
    bckstd = np.full((nt,), np.nan)
    if not forcelamb is True:
        dlamb = np.full((nt, nmax), np.nan)
        dlambstd = np.full((nt, nmax), np.nan)
    else:
        dlamb, dlambstd = None, None

    # Loop on spectra
    lch = []
    for ii in range(0, nspect):

        if verbose is not None and ii%nstr==0:
            print("=> spectrum {0} / {1}".format(ii+1, nspect))

        try:
            popt, pcov = scpopt.curve_fit(func_sca, x, spectra[ii,:],
                                          jac=func_sca_jac,
                                          p0=p0, bounds=bounds,
                                          max_nfev=max_nfev, xtol=xtol,
                                          x_scale='jac',
                                          verbose=verbose)
        except Exception as err:
            msg = "    Convergence issue for {0} / {1}\n".format(ii+1, nspect)
            msg += "    => %s\n"%str(err)
            msg += "    => Resetting initial guess and bounds..."
            print(msg)
            try:
                p0, bounds, _ = get_p0bounds(x, spectra[ii,:],
                                             nmax=nmax, lamb0=lamb0)
                popt, pcov = scpopt.curve_fit(func_sca, x, spectra[ii,:],
                                              jac=func_sca_jac,
                                              p0=p0, bounds=bounds,
                                              max_nfev=max_nfev, xtol=xtol,
                                              x_scale='jac',
                                              verbose=verbose)
                p0 = popt
                popt, pcov = scpopt.curve_fit(func_sca, x, spectra[ii,:],
                                              jac=func_sca_jac,
                                              p0=p0, bounds=bounds,
                                              max_nfev=max_nfev, xtol=xtol,
                                              x_scale='jac',
                                              verbose=verbose)
                lch.append(ii)
            except Exception as err:
                print(str(err))
                import ipdb
                ipdb.set_trace()
                raise err

        out = np.split(popt, indsplit)
        outstd = np.split(np.sqrt(np.diag(pcov)), indsplit)
        if forcelamb is True:
            amp[ii, :], sigma[ii, :], bck[ii] = out
            ampstd[ii, :], sigmastd[ii, :], bckstd[ii] = outstd
        else:
            amp[ii, :], dlamb[ii, :], sigma[ii, :], bck[ii] = out
            ampstd[ii,:], dlambstd[ii,:], sigmastd[ii,:], bckstd[ii] = outstd
        fit[ii, :] = func_sca(x, *popt)
        p0[:] = popt[:]

        if plot_debug and ii in [0,1]:
            fit = func_vect(x, amp[ii,:], x0[ii,:], sigma[ii,:], bck0[ii])

            plt.figure()
            ax0 = plt.subplot(2,1,1)
            ax1 = plt.subplot(2,1,2, sharex=ax0, sharey=ax0)
            ax0.plot(x,spectra[ii,:], '.k',
                     x, np.sum(fit, axis=0), '-r')
            ax1.plot(x, fit.T)

    std = np.sqrt(np.sum((spectra-fit)**2, axis=1))

    dout = {'fit': fit, 'lamb0': lamb0, 'std': std, 'lch': lch,
            'amp': amp, 'ampstd': ampstd,
            'sigma': sigma, 'sigmastd': sigmastd,
            'bck': bck, 'bckstd': bckstd,
            'dlamb': dlamb, 'dlambstd': dlambstd}

    return dout


###########################################################
###########################################################
#
#           1d spectral fitting from dlines
#
###########################################################
###########################################################

def _width_shift_amp(indict, keys=None, dlines=None, nlines=None):

    # ------------------------
    # Prepare error message
    msg = ''

    # ------------------------
    # Check case
    c0 = indict is False
    c1 = isinstance(indict, str)
    c2 = (isinstance(indict, dict)
          and all([isinstance(k0, str)
                   and (isinstance(v0, list) or isinstance(v0, str))
                   for k0, v0 in indict.items()]))
    c3 = (isinstance(indict, dict)
          and all([(ss in keys
                    and isinstance(vv, dict)
                    and all([s1 in ['coef', 'key'] for s1 in vv.keys()])
                    and isinstance(vv['key'], str))
                   for ss, vv in indict.items()]))
    c4 = (isinstance(indict, dict)
          and isinstance(indict.get('keys'), list)
          and isinstance(indict.get('ind'), np.ndarray))
    if not any([c0, c1, c2, c3, c4]):
        msg = ("Wrong input dict!\n"
               + "\t{}".format([c0, c1, c2, c3, c4]))
        raise Exception(msg)

    # ------------------------
    # str key to be taken from dlines as criterion
    if c0:
        lk = keys
        ind = np.eye(nlines)
        outdict = {'keys': lk, 'ind': ind, 'coefs': np.ones((nlines,))}

    if c1:
        lk = sorted(set([dlines[k0].get(indict, k0)
                         for k0 in keys]))
        ind = np.array([[dlines[k1].get(indict, k1) == k0
                         for k1 in keys] for k0 in lk])
        outdict = {'keys': lk, 'ind': ind, 'coefs': np.ones((nlines,))}

    elif c2:
        lkl = []
        for k0, v0 in indict.items():
            if isinstance(v0, str):
                v0 = [v0]
            if not (len(set(v0)) == len(v0)
                    and all([k1 in keys and k1 not in lkl for k1 in v0])):
                msg = ("Inconsistency in indict[{}], either:\n".format(k0)
                       + "\t- v0 not unique: {}\n".format(v0)
                       + "\t- some v0 not in keys: {}\n".format(keys)
                       + "\t- some v0 in lkl:      {}".format(lkl))
                raise Exception(msg)
            indict[k0] = v0
            lkl += v0
        for k0 in set(keys).difference(lkl):
            indict[k0] = [k0]
        lk = sorted(set(indict.keys()))
        ind = np.array([[k1 in indict[k0] for k1 in keys] for k0 in lk])
        outdict = {'keys': lk, 'ind': ind, 'coefs': np.ones((nlines,))}

    elif c3:
        lk = sorted(set([v0['key'] for v0 in indict.values()]))
        lk += sorted(set(keys).difference(indict.keys()))
        ind = np.array([[indict.get(k1, {'key': k1})['key'] == k0
                         for k1 in keys]
                        for k0 in lk])
        coefs = np.array([indict.get(k1, {'coef': 1.}).get('coef', 1.)
                          for k1 in keys])
        outdict = {'keys': lk, 'ind': ind, 'coefs': coefs}

    elif c4:
        outdict = indict
        if 'coefs' not in indict.keys():
            outdict['coefs'] = np.ones((nlines,))

    # ------------------------
    # Ultimate conformity checks
    if not c0:
        assert sorted(outdict.keys()) == ['coefs', 'ind', 'keys']
        assert isinstance(outdict['ind'], np.ndarray)
        assert outdict['ind'].dtype == np.bool_
        assert outdict['ind'].shape == (len(outdict['keys']), nlines)
        assert np.all(np.sum(outdict['ind'], axis=0) == 1)
        assert outdict['coefs'].shape == (nlines,)
    return outdict


def multigausfit1d_from_dlines_dinput(dlines=None,
                                      dconstraints=None,
                                      lambmin=None, lambmax=None,
                                      defconst=_DCONSTRAINTS):

    # ------------------------
    # Check / format basics
    # ------------------------

    # Select relevant lines (keys, lamb)
    keys = np.array([k0 for k0 in dlines.keys()])
    lamb = np.array([dlines[k0]['lambda'] for k0 in keys])
    if lambmin is not None:
        keys = keys[lamb >= lambmin]
        lamb = lamb[lamb >= lambmin]
    if lambmax is not None:
        keys = keys[lamb <= lambmax]
        lamb = lamb[lamb <= lambmax]
    inds = np.argsort(lamb)
    keys, lamb = keys[inds], lamb[inds]
    nlines = lamb.size

    # Check constraints
    if dconstraints is None:
        dconstraints =  defconst


    # ------------------------
    # Check keys
    # ------------------------

    # Check dconstraints keys
    lk = sorted(_DCONSTRAINTS.keys())
    c0= (isinstance(dconstraints, dict)
         and all([k0 in lk for k0 in dconstraints.keys()]))
    if not c0:
        raise Exception(msg)

    # copy to avoid modifying reference
    dconstraints = copy.deepcopy(dconstraints)

    dinput = {}

    # ------------------------
    # Check / format double
    # ------------------------

    dinput['double'] = dconstraints.get('double', defconst['double'])
    if type(dinput['double']) is not bool:
        raise Exception(msg)

    # ------------------------
    # Check / format width, shift, amp (groups with posssible ratio)
    # ------------------------
    for k0 in ['amp', 'width', 'shift']:
        dinput[k0] = _width_shift_amp(dconstraints.get(k0, defconst[k0]),
                                      keys=keys, nlines=nlines, dlines=dlines)

    # ------------------------
    # add mz, symb, ION, keys, lamb
    # ------------------------
    dinput['mz'] = np.array([dlines[k0].get('m', np.nan) for k0 in keys])
    dinput['symb'] = np.array([dlines[k0].get('symbol', k0) for k0 in keys])
    dinput['ion'] = np.array([dlines[k0].get('ION', '?') for k0 in keys])

    dinput['keys'] = keys
    dinput['lines'] = lamb
    dinput['nlines'] = nlines

    dinput['Ti'] = dinput['width']['ind'].shape[0] < nlines
    dinput['vi'] = dinput['shift']['ind'].shape[0] < nlines

    return dinput


def multigausfit1d_from_dlines_ind(dinput=None):
    """ Return the indices of quantities in x to compute y """

    # indices
    # General shape: [bck, amp, widths, shifts]
    # If double [..., double_shift, double_ratio]
    # Excpet for bck, all indices should render nlines (2*nlines if double)
    dind = {'bck': np.r_[0], 'dshift': None, 'dratio': None}
    nn = dind['bck'].size
    inddratio, inddshift = None, None
    for k0 in ['amp', 'width', 'shift']:
        lnl = np.sum(dinput[k0]['ind'], axis=1).astype(int)
        dind[k0] = {'x': nn + np.arange(0, dinput[k0]['ind'].shape[0]),
                    'lines': nn + np.argmax(dinput[k0]['ind'], axis=0),
                    'jac': [tuple(dinput[k0]['ind'][ii, :].nonzero()[0])
                            for ii in range(dinput[k0]['ind'].shape[0])]}
        nn += dind[k0]['x'].size

    sizex = dind['shift']['x'][-1] + 1
    indx = np.r_[dind['bck'], dind['amp']['x'],
                 dind['width']['x'], dind['shift']['x']]
    assert np.all(np.arange(0, sizex) == indx)

    # check if double
    if dinput['double']:
        dind['dshift'] = -2
        dind['dratio'] = -1
        sizex += 2

    dind['sizex'] = sizex
    dind['shapey1'] = dind['bck'].size + dinput['nlines']

    # Ref line for amp (for x0)
    amp_x0 = np.zeros((dinput['amp']['ind'].shape[0],), dtype=int)
    for ii in range(dinput['amp']['ind'].shape[0]):
        indi = dinput['amp']['ind'][ii, :].nonzero()[0]
        amp_x0[ii] = indi[np.argmin(np.abs(dinput['amp']['coefs'][indi]-1.))]
    dind['amp_x0'] = amp_x0

    return dind

def multigausfit1d_from_dlines_scale(data, lamb,
                                     scales=None, nspect=None,
                                     chain=None):
    if scales is None:
        Dlamb = lamb[-1]-lamb[0]
        lambm = np.nanmin(lamb)
        # bck, amp, width, shift
        if chain is True:
            scales = np.r_[np.nanmin(data[0, :]),
                           np.nanmax(data[0, :]),
                           (Dlamb/(20*lambm))**2,
                           Dlamb/(50*lambm)][None, :]
            scales = np.tile(scales, (nspect, 1))
        else:
            scales = np.array([np.nanmin(data, axis=1),
                               np.nanmax(data, axis=1),
                               np.full((nspect,), (Dlamb/(20*lambm))**2),
                               np.full((nspect,), Dlamb/(50*lambm))]).T
    assert scales.ndim in [1, 2]
    if scales.ndim == 1:
        scales = np.tile(scales, (nspect, scales.size))
    assert scales.shape == (nspect, 4)
    return scales

def _checkformat_dx0(amp_x0=None, keys=None, dx0=None):
    # Check
    c0 = dx0 is None
    c1 = (isinstance(dx0, dict)
          and all([k0 in keys for k0 in dx0.keys()]))
    c2 = (isinstance(dx0, dict)
          and sorted(dx0.keys()) == ['amp']
          and isinstance(dx0['amp'], np.ndarray))
    if not any([c0, c1, c2]):
        msg = ("dx0 must be a dict of the form:\n"
               + "\t{k0: {'amp': float},\n"
               + "\t k1: {'amp': float},\n"
               + "\t ...,\n"
               + "\t kn: {'amp': float}\n"
               + "where [k0, k1, ..., kn] are keys of spectral lines")
        raise Exception(msg)

    # Build
    if c0:
        dx0 = {'amp': np.ones((amp_x0.size,))}
    elif c1:
        coefs = np.array([dx0.get(keys[ii], {'amp': 1.}).get('amp', 1.)
                          for ii in amp_x0])
        dx0 = {'amp': coefs}
    elif c2:
        assert dx0['amp'].shape == (amp_x0.size,)
    return dx0


def multigausfit1d_from_dlines_x0(dind=None,
                                  lines=None, data=None, lamb=None,
                                  scales=None, double=None, dx0=None,
                                  chain=None, nspect=None, keys=None):
    # user-defined coefs on amplitude
    dx0 = _checkformat_dx0(amp_x0=dind['amp_x0'], keys=keys, dx0=dx0)

    # indlines for amp
    # (to take the lines with coefs = 1)
    # (and also to take the lines in amp order!)
    linesbis = lines[dind['amp_x0']]

    # Each x0 should be understood as x0*scale
    x0_scale = np.full((nspect, dind['sizex']), np.nan)
    if chain is True:
        amp0 = data[0, np.searchsorted(lamb, linesbis)]
        x0_scale[0, dind['amp']['x']] = amp0 / scales[0, 1]
        x0_scale[0, dind['bck']] = 1.
        x0_scale[0, dind['width']['x']] = 0.4
        x0_scale[0, dind['shift']['x']] = 0.
        if double is True:
            x0_scale[0, dind['dratio']] = 1.2
            x0_scale[0, dind['dshift']] = -0.5
        x0_scale[0, dind['amp']['x']] *= dx0['amp']
    else:
        amp0 = data[:, np.searchsorted(lamb, linesbis)]
        x0_scale[:, dind['amp']['x']] = amp0 / scales[:, 1:2]
        x0_scale[:, dind['bck']] = 1.
        x0_scale[:, dind['width']['x']] = 0.4
        x0_scale[:, dind['shift']['x']] = 0.
        if double is True:
            x0_scale[:, dind['dratio']] = 0.7
            x0_scale[:, dind['dshift']] = 0.7
        x0_scale[:, dind['amp']['x']] *= dx0['amp']
    return x0_scale

def multigausfit1d_from_dlines_bounds(sizex=None, dind=None, double=None):
    # Each x0 should be understood as x0*scale
    xup = np.full((sizex,), np.nan)
    xlo = np.full((sizex,), np.nan)
    xup[dind['bck']] = 2.
    xlo[dind['bck']] = 0.
    xup[dind['amp']['x']] = 1
    xlo[dind['amp']['x']] = 0.
    xup[dind['width']['x']] = 1.
    xlo[dind['width']['x']] = 0.01
    xup[dind['shift']['x']] = 1.
    xlo[dind['shift']['x']] = -1.
    if double is True:
        xup[dind['dratio']] = 1.6
        xlo[dind['dratio']] = 0.4
        xup[dind['dshift']] = 10.
        xlo[dind['dshift']] = -10.
    bounds_scale = (xlo, xup)
    return bounds_scale

def multigausfit1d_from_dlines_funccostjac(lamb,
                                           dinput=None,
                                           dind=None,
                                           scales=None,
                                           jac=None):
    indbck = dind['bck']
    inda = dind['amp']['x']
    indw = dind['width']['x']
    inds = dind['shift']['x']
    inddratio = dind['dratio']
    inddshift = dind['dshift']

    indal = dind['amp']['lines']
    indwl = dind['width']['lines']
    indsl = dind['shift']['lines']

    indaj = dind['amp']['jac']
    indwj = dind['width']['jac']
    indsj = dind['shift']['jac']

    coefsal = dinput['amp']['coefs']
    coefswl = dinput['width']['coefs']
    coefssl = dinput['shift']['coefs']

    shape = (lamb.size, dind['shapey1'])

    def func_detail(x, lamb=lamb[:, None],
                    lines=dinput['lines'][None, :],
                    double=dinput['double'],
                    shape=shape,
                    indbck=indbck, indal=indal, indwl=indwl, indsl=indsl,
                    inddratio=inddratio, inddshift=inddshift,
                    coefsal=coefsal, coefswl=coefswl, coefssl=coefssl,
                    scales=scales):
        y = np.full(shape, np.nan)
        y[:, 0] = x[indbck] * scales[0]

        # lines
        amp = (scales[1]*x[indal]*coefsal)[None, :]
        wi2 = (scales[2]*x[indwl]*coefswl)[None, :]
        shifti = (scales[3]*x[indsl]*coefssl)[None, :]
        y[:, 1:] = amp * np.exp(-(lamb/lines - (1 + shifti))**2 / (2*wi2))

        if double is True:
            ampd = amp*x[inddratio]  # (scales[1]*x[indal]*x[inddratio]*coefsal)[None, :]
            shiftid = (scales[3]*(x[indsl]+x[inddshift])*coefssl)[None, :]
            y[:, 1:] += (ampd
                         * np.exp(-(lamb/lines - (1 + shiftid))**2 / (2*wi2)))
        return y

    def cost(x, data=None, scales=None):
        return (np.sum(func_detail(x, scales=scales), axis=1) - data)

    if jac == 'call':
        # Define a callable jac returning (nlamb, sizex) matrix of partial
        # derivatives of np.sum(func_details(scaled), axis=0)
        def jac(x,
                lamb=lamb[:, None],
                lines=dinput['lines'][None, :],
                indbck=indbck, indal=indal, indwl=indwl,
                indsl=indsl, inddratio=inddratio, inddshift=inddshift,
                inda=inda, indw=indw, inds=inds,
                indaj=indaj, indwj=indwj, indsj=indsj,
                coefsal=coefsal, coefswl=coefswl, coefssl=coefssl,
                scales=None, double=dinput['double'], data=None):
            jac = np.full((lamb.size, x.size), np.nan)
            jac[:, 0] =scales[0]

            # Assuming Ti = False and vi = False
            amp = (scales[1]*x[indal]*coefsal)[None, :]
            wi2 = (scales[2]*x[indwl]*coefswl)[None, :]
            shifti = (scales[3]*x[indsl]*coefssl)[None, :]
            beta = (lamb/lines - (1 + shifti)) / (2*wi2)
            alpha = -beta**2 * (2*wi2)
            exp = np.exp(alpha)

            quant = scales[1] * coefsal[None, :] * exp
            for ii in range(inda.size):
                jac[:, inda[ii]] = np.sum(quant[:, indaj[ii]], axis=1)
            quant = amp * (-alpha/x[indwl][None, :]) * exp
            for ii in range(indw.size):
                jac[:, indw[ii]] = np.sum(quant[:, indwj[ii]], axis=1)
            quant = amp * 2.*beta*scales[3]*coefssl[None,:] * exp
            for ii in range(inds.size):
                jac[:, inds[ii]] = np.sum(quant[:, indsj[ii]], axis=1)
            if double is True:
                # Assuming Ti = False and vi = False
                ampd = amp*x[inddratio]
                shiftid = (scales[3]*(x[indsl]+x[inddshift])*coefssl)[None, :]
                betad = (lamb/lines - (1 + shiftid)) / (2*wi2)
                alphad = -betad**2 * (2*wi2)
                expd = np.exp(alphad)

                quant = scales[1] * coefsal[None, :] * expd
                for ii in range(inda.size):
                    jac[:, inda[ii]] += np.sum(quant[:, indaj[ii]], axis=1)
                quant = ampd * (-alphad/x[indwl][None, :]) * expd
                for ii in range(indw.size):
                    jac[:, indw[ii]] += np.sum(quant[:, indwj[ii]], axis=1)
                quant = ampd * 2.*betad*scales[3]*coefssl[None,:] * expd
                for ii in range(inds.size):
                    jac[:, inds[ii]] += np.sum(quant[:, indsj[ii]], axis=1)

                jac[:, inddratio] = np.sum(ampd * expd, axis=1)
                jac[:, inddshift] = np.sum(ampd * 2.*betad*scales[3] * expd,
                                           axis=1)
            return jac
    else:
        if jac not in ['2-point', '3-point']:
            msg = "jac should be in ['call', '2-point', '3-point']"
            raise Exception(msg)
        jac = jac

    return func_detail, cost, jac


def multigausfit1d_from_dlines(data, lamb,
                               lambmin=None, lambmax=None,
                               dinput=None, dx0=None, ratio=None,
                               scales=None, x0_scale=None, bounds_scale=None,
                               method=None, max_nfev=None,
                               xtol=None, ftol=None, gtol=None,
                               chain=None, verbose=None,
                               loss=None, jac=None):
    """ Solve multi_gaussian fit in 1d from dlines

    If Ti is True, all lines from the same ion have the same width
    If vi is True, all lines from the same ion have the same normalised shift
    If double is True, all lines are double with common shift and ratio

    Unknowns are:
        x = [bck, w0, v0, c00, c01, ..., c0n, w1, v1, c10, c11, ..., c1N, ...]

        - bck : constant background
        - wi  : spectral width of a group of lines (ion): wi^2 = 2kTi / m*c**2
                This way, it is dimensionless
        - vni : normalised velicity of the ion: vni = vi / c
        - cij : normalised coef (intensity) of line: cij = Aij

    Scaling is done so each quantity is close to unity:
        - bck: np.mean(data[data < mean(data)/2])
        - wi : Dlamb / 20
        - vni: 10 km/s
        - cij: np.mean(data)

    """

    # Check format
    if chain is None:
        chain = True
    if jac is None:
        jac = 'call'
    if method is None:
        method = 'trf'
    assert method in ['trf', 'dogbox'], method
    if xtol is None:
        xtol = 1.e-12
    if ftol is None:
        ftol = 1.e-12
    if gtol is None:
        gtol = 1.e-12
    if loss is None:
        loss = 'linear'
    if max_nfev is None:
        max_nfev = None
    if verbose is None:
        verbose = 1
    if verbose == 2:
        verbscp = 2
    else:
        verbscp = 0

    assert lamb.ndim == 1
    assert data.ndim in [1, 2] and lamb.size in data.shape
    if data.ndim == 1:
        data = data[None, :]
    if data.shape[1] != lamb.size:
        data = data.T
    nspect = data.shape[0]

    # ---------------------------
    # Prepare
    assert np.allclose(np.unique(lamb), lamb)
    nlines = dinput['nlines']

    # Get indices dict
    dind = multigausfit1d_from_dlines_ind(dinput)

    # Get scaling
    scales = multigausfit1d_from_dlines_scale(data, lamb,
                                              scales=scales, nspect=nspect,
                                              chain=chain)

    # Get initial guess
    x0_scale = multigausfit1d_from_dlines_x0(dind=dind,
                                             lines=dinput['lines'],
                                             data=data,
                                             lamb=lamb,
                                             scales=scales,
                                             double=dinput['double'],
                                             nspect=nspect,
                                             chain=chain,
                                             dx0=dx0, keys=dinput['keys'])

    # get bounds
    bounds_scale = multigausfit1d_from_dlines_bounds(dind['sizex'],
                                                     dind,
                                                     dinput['double'])

    # Get function, cost function and jacobian
    (func_detail,
     cost, jacob) = multigausfit1d_from_dlines_funccostjac(lamb,
                                                           dinput=dinput,
                                                           dind=dind,
                                                           jac=jac)

    # ---------------------------
    # Optimize

    # Initialize
    nlines = dinput['nlines']
    sol_detail = np.full((nspect, dind['shapey1'], lamb.size), np.nan)
    amp = np.full((nspect, nlines), np.nan)
    width2 = np.full((nspect, nlines), np.nan)
    shift = np.full((nspect, nlines), np.nan)
    coefs = np.full((nspect, nlines), np.nan)
    if dinput['double'] is True:
        dratio = np.full((nspect,), np.nan)
        dshift = np.full((nspect, nlines), np.nan)
    else:
        dratio, dshift = None, None
    kTiev, vims = None, None
    if dinput['Ti'] is True:
        conv = np.sqrt(scpct.mu_0*scpct.c / (2.*scpct.h*scpct.alpha))
        kTiev = np.full((nspect, dinput['width']['ind'].shape[0]), np.nan)
    if dinput['vi'] is True:
        indvi = np.array([iit[0] for iit in dind['shift']['jac']])
        vims = np.full((nspect, dinput['shift']['ind'].shape[0]), np.nan)

    # Prepare msg
    if verbose > 0:
        msg = ("Loop in {} spectra with jac = {}\n".format(nspect, jac)
               + "time (s)    cost   nfev   njev   term"
               + "-"*20)
        print(msg)

    # Minimize
    for ii in range(nspect):
        t0 = dtm.datetime.now()     # DB
        res = scpopt.least_squares(cost, x0_scale[ii, :],
                                   jac=jacob, bounds=bounds_scale,
                                   method=method, ftol=ftol, xtol=xtol,
                                   gtol=gtol, x_scale=1.0, f_scale=1.0,
                                   loss=loss, diff_step=None,
                                   tr_solver=None, tr_options={},
                                   jac_sparsity=None, max_nfev=max_nfev,
                                   verbose=verbscp, args=(),
                                   kwargs={'data': data[ii, :],
                                           'scales': scales[ii, :]})
        if chain is True and ii < nspect-1:
            x0_scale[ii+1, :] = res.x
        if verbose > 0:
            dt = round((dtm.datetime.now()-t0).total_seconds(), ndigits=3)
            msg = " {}    {}    {}   {}   {}".format(dt, round(res.cost),
                                                     res.nfev, res.njev,
                                                     res.message)
            print(msg)

        # Separate and reshape output
        sol_detail[ii, ...] = func_detail(res.x, scales=scales[ii, :]).T

        # Get result in physical units: TBC !!!
        amp[ii, :] = (res.x[dind['amp']['lines']]
                      * scales[ii, 1] * dinput['amp']['coefs'])
        width2[ii, :] = (res.x[dind['width']['lines']]
                         * scales[ii, 2] * dinput['width']['coefs'])
        shift[ii, :] = (res.x[dind['shift']['lines']]
                        * scales[ii, 3] * dinput['shift']['coefs']
                        * dinput['lines'])
        if dinput['double'] is True:
            dratio[ii] = res.x[dind['dratio']]
            dshift[ii, :] = (res.x[dind['dshift']]
                             * scales[ii, 3] * dinput['lines'])
        if dinput['vi'] is True:
            vims[ii, :] = (res.x[dind['shift']['lines'][indvi]]
                           * scales[ii, 3] * scpct.c)

    coefs = amp*dinput['lines']*np.sqrt(2*np.pi*width2)
    if dinput['Ti'] is True:
        # Get Ti in eV and vi in m/s
        ind = np.array([iit[0] for iit in dind['width']['jac']])
        kTiev = conv * width2[:, ind] * dinput['mz'][ind] * scpct.c**2

    # Extract ratio of lines
    if ratio is not None:
        # Te can only be obtained as a proxy, units don't matter at this point
        if isinstance(ratio['up'], str):
            ratio['up'] = [ratio['up']]
        if isinstance(ratio['low'], str):
            ratio['low'] = [ratio['low']]
        assert len(ratio['up']) == len(ratio['low'])
        indup = np.array([(dinput['keys'] == uu).nonzero()[0][0]
                          for uu in ratio['up']])
        indlow = np.array([(dinput['keys'] == ll).nonzero()[0][0]
                           for ll in ratio['low']])
        ratio['value'] = coefs[:, indup] / coefs[:, indlow]
        ratio['str'] = ["{}/{}".format(dinput['symb'][indup[ii]],
                                       dinput['symb'][indlow[ii]])
                        for ii in range(len(ratio['up']))]

    # Create output dict
    dout = {'data': data, 'lamb': lamb,
            'sol_detail': sol_detail,
            'sol': np.sum(sol_detail, axis=1),
            'Ti': dinput['Ti'], 'vi': dinput['vi'], 'double': dinput['double'],
            'width2': width2, 'shift': shift, 'amp': amp,
            'dratio': dratio, 'dshift': dshift, 'coefs': coefs,
            'kTiev': kTiev, 'vims': vims, 'ratio': ratio,
            'cost': res.cost, 'fun': res.fun, 'active_mask': res.active_mask,
            'nfev': res.nfev, 'njev': res.njev, 'status': res.status,
            'msg': res.message, 'success': res.success}
    return dout


###########################################################
###########################################################
#
#           2d spectral fitting
#
###########################################################
###########################################################

def get_knots_nbs_for_bsplines(knots_unique, deg):
    if deg > 0:
        knots = np.r_[[knots_unique[0]]*deg, knots_unique,
                      [knots_unique[-1]]*deg]
    else:
        knots = knots_unique
    nbknotsperbs = 2 + deg
    nbs = knots_unique.size - 1 + deg
    assert nbs == knots.size - 1 - deg
    return knots, nbknotsperbs, nbs


def multigausfit2d_from_dlines_ind(dlines2=None,
                                   double=None, nbs=None,
                                   Ti=None, vi=None, dconst=None):
    """ Return the indices of quantities in x to compute y """

    # Prepare lines concatenation
    nlines = dlines2['key'].size
    nion = len(dlines2['ion_u'])
    nwidth = len(dlines2['width_u'])
    nshift = len(dlines2['shift_u'])
    lnlines_i = [np.sum(dlines2['ion'] == ii) for ii in dlines2['ion_u']]
    lnlines_w = [np.sum(dlines2['width'] == ww) for ww in dlines2['width_u']]
    lnlines_s = [np.sum(dlines2['shift'] == ss) for ss in dlines2['shift_u']]
    assert np.sum(lnlines_w) == nlines
    assert np.sum(lnlines_s) == nlines

    # indices
    # General shape: [bck, widths, shifts, amp]
    # If double [..., double_shift, double_ratio]
    # Excpet for bck, all indices should render nlines (2*nlines if double)
    indbck = np.arange(0, nbs)
    inddratio, inddshift = None, None
    if Ti is False and vi is False:
        indw = nbs + np.arange(0, nlines*nbs)
        indw_lines = indw
        inds = indw + nlines*nbs
        inds_lines = inds
        inda = inds + nlines*nbs
        inda_lines = inda
        sizex = nbs*(1 + 3*nlines)
    elif Ti is True and vi is False:
        indw = nbs + np.arange(0, nwidth*nbs)
        indw_lines = np.repeat(indw, lnlines_w)
        inds = nbs + nwidth*nbs + np.arange(0, nlines*nbs)
        inds_lines = inds
        inda = inds + nlines*nbs
        inda_lines = inda
        sizex = nbs*(1 + nwidth + 2*nlines)
    elif Ti is False and vi is True:
        indw = nbs + np.arange(0, nlines*nbs)
        indw_lines = indw
        inds = nbs + nlines*nbs + np.arange(0, nshift*nbs)
        inds_lines = np.repeat(inds, lnlines_s)
        inda = indw + nshift*nbs + nlines*nbs
        inda_lines = inda
        sizex = nbs*(1 + nshift + 2*nlines)
    else:
        indw = nbs + np.arange(0, nwidth*nbs)
        indw_lines = np.repeat(indw, lnlines_w)
        inds = nbs + nwidth*nbs + np.arange(0, nshift*nbs)
        inds_lines = np.repeat(inds, lnlines_s)
        inda = nbs + nwidth*nbs + nshift*nbs + np.arange(0, nlines*nbs)
        inda_lines = inda
        sizex = nbs*(1 + nwidth + nshift + nlines)
    shapey0 = 1 + nlines

    # index to get back unique ions values from width and shift
    indions = np.repeat(np.arange(0, nion**nbs), lnlines_i)
    # TBC...
    indions_back = np.r_[0, np.cumsum(lnlines_i[:-1])]

    if double:
        inddshift = -2
        inddratio = -1
        sizex += 2

    # Indices for jacobian
    if Ti is True:
        indw_jac = np.r_[0, np.cumsum(nbs*lnlines_w[:-1])]
    else:
        indw_jac = np.arange(0, nlines*nbs)

    if vi is True:
        inds_jac = np.r_[0, np.cumsum(nbs*lnlines_s[:-1])]
    else:
        inds_jac = np.arange(0, nlines*nbs)


    # Take into account amplitude ratio constraints
    if dconst is not None and dconst.get(['ratio']) is not None:
        lup = sorted(set([rr['up'] for rr in dconst['ratio']]))
        llow = sorted(set([rr['low'] for rr in dconst['ratio']]))

        # Remove upper amp from xi
        # TBF !!!!

        for ii, rr in enumerate(dconst['ratio']):
            indup = (dlines2['key'] == rr['up']).nonzero()[0][0]
            indup = (dlines2['key'] == rr['low']).nonzero()[0][0]
            dconst['ratio'][ii]['indup'] = indup
            dconst['ratio'][ii]['indlow'] = indlow

            # Remove upper from x

    dind = {'bck': indbck,
            'width': indw, 'shift': inds, 'amp': inda,
            'width_lines': indw_lines, 'shift_lines': inds_lines,
            'amp_lines': inda_lines, 'width_jac': indw_jac,
            'shift_jac': inds_jac,
            'dratio': inddratio, 'dshift': inddshift,
            'ions': indions, 'ions_back': indions_back,
            }
    return dind, sizex, shapey0


def multigausfit2d_from_dlines_scale(data2d, lambfit, phifit,
                                     lambmin=None, lambmax=None, dlines2=None,
                                     Ti=None, vi=None, double=None,
                                     xtol=None, ftol=None, gtol=None,
                                     method=None, max_nfev=None,
                                     loss=None, jac=None):

    # Extract nbs spect1d for 1d fitting
    for ii in range(nbs):
        if np.any(np.isnan(spect1d)):
            continue
        dfit1d = multigausfit1d_from_dlines(spect1d, lambfit,
                                            lambmin=lambmin, lambmax=lambmax,
                                            dlines2=dlines2, ratio=None,
                                            dscale=None, x0_scale=None,
                                            bounds_scale=None,
                                            method=method, max_nfev=max_nfev,
                                            xtol=xtol, ftol=ftol, gtol=gtol,
                                            Ti=Ti, vi=vi, double=double,
                                            verbose=None,
                                            loss=loss, jac=jac)
        bck[ii] = dfit1d['bck']
        amp[ii] = dfit1d['amp']
        width[ii] = dfit1d['width']
        shift[ii] = dfit1d['shift']

    # Interpolate cases that could not be run
    indnan = np.isnan(bck)
    if np.any(indnan):
        indok = ~indnan
        bck[indnan] = scpinterp.interp1d(phifit[indok], bck[indok],
                                         phifit[indnan])
        amp[indnan] = scpinterp.interp1d(phifit[indok], amp[indok],
                                         phifit[indnan])
    # Return
    dscale = {'bck': bck, 'amp': amp, 'width': width, 'shift': shift}
    return dscale


def multigausfit2d_from_dlines_x0(sizex, dind,
                                  lines=None, data_lamb_nbs=None, lamb=None,
                                  dscale=None, double=None):
    # Each x0 should be understood as x0*scale
    x0_scale = np.ones((sizex,), dtype=float)
    # x0_scale = np.full((sizex,), np.nan)
    # x0_scale[dind['bck']] = 1.
    # amp0 = [da[np.searchsorted(lamb, lines)] for da in data_lamb_nbs]
    # x0_scale[dind['amp']] = amp0 / dscale['amp']
    # x0_scale[dind['width']] = 0.4
    # x0_scale[dind['shift']] = 0.
    # if double is True:
        # x0_scale[dind['dratio']] = 0.8
        # x0_scale[dind['dshift']] = 0.2
    return x0_scale


# def get_2dspectralfit_func(lamb0, forcelamb=False,
                           # deg=None, knots=None):

    # lamb0 = np.atleast_1d(lamb0).ravel()
    # nlamb = lamb0.size
    # knots = np.atleast_1d(knots).ravel()
    # nknots = knots.size
    # nbsplines = np.unique(knots).size - 1 + deg

    # # Define function
    # def func(lamb, phi,
             # camp=None, cwidth=None, cshift=None,
             # lamb0=lamb0, nlamb=nlamb,
             # knots=knots, deg=deg, forcelamb=forcelamb,
             # nbsplines=nbsplines, mesh=True):
        # assert phi.ndim in [1, 2]
        # if camp is not None:
            # assert camp.shape[0] == nbsplines
            # bsamp = BSpline(knots, camp, deg,
                            # extrapolate=False, axis=0)
        # if csigma is not None:
            # assert csigma.shape[0] == nbsplines
            # bssigma = BSpline(knots, csigma, deg,
                              # extrapolate=False, axis=0)
        # if mesh or phi.ndim == 2:
            # lamb0 = lamb0[None, None, :]
        # else:
            # lamb0 = lamb0[None, :]
        # if forcelamb:
            # if mesh:
                # assert angle.ndim == lamb.ndim == 1
                # # shape (lamb, angle, lines)
                # return np.sum(bsamp(phi)[None,:,:]
                              # * np.exp(-(lamb[:,None,None]
                                         # - lamb0)**2
                                       # /(bssigma(phi)[None,:,:]**2)), axis=-1)
            # else:
                # assert phi.shape == lamb.shape
                # lamb = lamb[..., None]
                # # shape (lamb/angle, lines)
                # return np.sum(bsamp(phi)
                              # * np.exp(-(lamb
                                         # - lamb0)**2
                                       # /(bssigma(phi)**2)), axis=-1)
        # else:
            # if cdlamb is not None:
                # assert cdlamb.shape[0] == nbsplines
                # bsdlamb = BSpline(knots, cdlamb, deg,
                                  # extrapolate=False, axis=0)

    # return func


# def get_multigaussianfit2d_costfunc(lamb=None, phi=None, data=None, std=None,
                                    # lamb0=None, forcelamb=None,
                                    # deg=None, knots=None,
                                    # nlamb0=None, nkperbs=None, nbs=None,
                                    # nc=None, debug=None):
    # assert lamb.shape == phi.shape == data.shape
    # assert lamb.ndim == 1
    # assert nc == nbs*nlamb0

    # if forcelamb is None:
        # forcelamb = False
    # if debug is None:
        # debug = False

    # # Define func assuming all inpus properly formatted
    # if forcelamb:
        # # x = [camp[1-nbs,...,nbs*(nlamb0-1)-nc}, csigma[1-nc]]
        # def func(x,
                 # lamb=lamb, phi=phi, data=data, std=std,
                 # lamb0=lamb0, knots=knots, deg=deg, nc=nc):
            # amp = BSpline(knots, x[:nc], deg,
                          # extrapolate=False, axis=0)(phi)
            # sigma = BSpline(knots, x[nc:], deg,
                            # extrapolate=False, axis=0)(phi)
            # val = np.sum(amp[:, None]
                         # * np.exp(-(lamb[:, None] - lamb0[None, :])**2
                                  # /(sigma[:, None]**2)), axis=-1)
            # return (val-data)/(std*data.size)

        # def jac(x,
                # lamb=lamb, phi=phi, std=std,
                # lamb0=lamb0, knots=knots, deg=deg,
                # nlamb0=nlamb0, nkperbs=nkperbs, nbs=nbs, nc=nc):
            # amp = BSpline(knots, x[:nc], deg,
                          # extrapolate=False, axis=0)(phi)
            # sigma = BSpline(knots, x[nc:], deg,
                            # extrapolate=False, axis=0)(phi)
            # jacx = sparse.csr_matrix((phi.size, 2*nc), dtype=float)
            # #jacx = np.zeros((phi.size, 2*nc), dtype=float)
            # for ii in range(nlamb0):
                # expi = np.exp(-(lamb-lamb0[ii])**2/sigma**2)
                # for jj in range(nbs):
                    # ind = ii*nbs + jj
                    # indk = np.r_[jj*nkperbs:(jj+1)*nkperbs]
                    # # all bsplines are the same, only coefs (x) are changing
                    # bj = BSpline.basis_element(knots[indk],
                                               # extrapolate=False)(phi)
                    # #bj[np.isnan(bj)] = 0.
                    # indok = ~np.isnan(bj)
                    # # Differentiate wrt camp
                    # jacx[indok, ind] = (bj * expi)[indok]
                    # # Differentiate wrt csigma
                    # jacx[indok, nc+ind] = (
                        # amp * (2*(lamb-lamb0[ii])**2*bj/sigma**3) * expi
                    # )[indok]
            # return jacx/(std*phi.size)
    # else:
        # # x = [camp1-nbs*nlamb, csigma1-nbs*nlamb, cdlamb1-nbs*nlamb]
        # def func(x,
                 # lamb=lamb, phi=phi, data=data, std=std,
                 # lamb0=lamb0, knots=knots, deg=deg,
                 # nbs=nbs, nlamb0=nlamb0, nc=nc, debug=debug):
            # amp = BSpline(knots, x[:nc].reshape((nbs, nlamb0), order='F'),
                          # deg, extrapolate=False, axis=0)(phi)
            # sigma = BSpline(knots, x[nc:2*nc].reshape((nbs, nlamb0), order='F'),
                            # deg, extrapolate=False, axis=0)(phi)
            # dlamb = BSpline(knots, x[2*nc:-1].reshape((nbs, nlamb0), order='F'),
                            # deg, extrapolate=False, axis=0)(phi)
            # val = np.nansum(amp
                            # * np.exp(-(lamb[:, None] - (lamb0[None, :]+dlamb))**2
                                  # / sigma**2),
                            # axis=-1) + x[-1]
            # if debug:
                # vmin, vmax = 0, np.nanmax(data)
                # fig = plt.figure(figsize=(14, 10));
                # ax0 = fig.add_axes([0.05,0.55,0.25,0.4])
                # ax1 = fig.add_axes([0.35,0.55,0.25,0.4], sharex=ax0, sharey=ax0)
                # ax2 = fig.add_axes([0.65,0.55,0.25,0.4], sharex=ax0, sharey=ax0)
                # ax3 = fig.add_axes([0.05,0.05,0.25,0.4], sharex=ax0, sharey=ax0)
                # ax4 = fig.add_axes([0.35,0.05,0.25,0.4], sharex=ax0, sharey=ax0)
                # ax5 = fig.add_axes([0.65,0.05,0.25,0.4], sharex=ax0, sharey=ax0)
                # ax0.scatter(lamb, phi, c=data, s=2, marker='s', edgecolors='None',
                           # vmin=vmin, vmax=vmax)  # DB
                # ax1.scatter(lamb, phi, c=val, s=2, marker='s', edgecolors='None',  # DB
                           # vmin=vmin, vmax=vmax)  # DB
                # errmax = np.nanmax(np.abs((val-data) / (std*data.size)))
                # ax2.scatter(lamb, phi, c=(val-data) / (std*data.size),
                            # s=2, marker='s', edgecolors='None',  # DB
                            # vmin=-errmax, vmax=errmax, cmap=plt.cm.seismic)  # DB
                # dlamb0_amp = np.max(np.diff(lamb0))/np.nanmax(np.abs(amp))
                # dlamb0_sigma = np.max(np.diff(lamb0))/np.nanmax(np.abs(sigma))
                # dlamb0_dlamb = np.max(np.diff(lamb0))/np.nanmax(np.abs(dlamb))
                # for ii in range(nlamb0):
                    # ax3.axvline(lamb0[ii], ls='--', c='k')
                    # ax4.axvline(lamb0[ii], ls='--', c='k')
                    # ax5.axvline(lamb0[ii], ls='--', c='k')
                    # ax3.plot(lamb0[ii] + dlamb0_amp*amp[:, ii], phi, '.', ms=4)
                    # ax4.plot(lamb0[ii] + dlamb0_sigma*sigma[:, ii], phi, '.', ms=4)
                    # ax5.plot(lamb0[ii] + dlamb0_dlamb*dlamb[:, ii], phi, '.', ms=4)
                # import ipdb         # DB
                # ipdb.set_trace()    # DB
            # return (val-data) / (std*data.size)

        # def jac(x,
                # lamb=lamb, phi=phi, std=std,
                # lamb0=lamb0, knots=knots, deg=deg,
                # nlamb0=nlamb0, nkperbs=nkperbs, nbs=nbs, nc=nc):
            # amp = BSpline(knots, x[:nc], deg,
                          # extrapolate=False, axis=0)(phi)
            # sigma = BSpline(knots, x[nc:2*nc], deg,
                            # extrapolate=False, axis=0)(phi)
            # dlamb = BSpline(knots, x[2*nc:], deg,
                            # extrapolate=False, axis=0)(phi)
            # #jacx = sparse.csr_matrix((phi.size, 2*nc), dtype=float)
            # jacx = np.zeros((phi.size, 3*nc+1), dtype=float)
            # for ii in range(nlamb0):
                # expi = np.exp(-(lamb-(lamb0[ii]+dlamb))**2/sigma**2)
                # indlamb = expi > 0.001
                # for jj in range(nbs):
                    # kk = ii*nbs + jj
                    # indk = jj + np.r_[:nkperbs]
                    # # all bsplines are the same, only coefs (x) are changing
                    # bj = BSpline.basis_element(knots[indk],
                                               # extrapolate=False)(phi)
                    # # bj[np.isnan(bj)] = 0.
                    # indok = (~np.isnan(bj)) & indlamb
                    # # Differentiate wrt camp
                    # jacx[indok, kk] = (bj[indok] * expi[indok])
                    # # Differentiate wrt csigma
                    # jacx[indok, nc+kk] = (
                        # amp * 2*(lamb-(lamb0[ii]+dlamb))**2*bj/sigma**3 * expi
                    # )[indok]
                    # # Differentiate wrt dlamb
                    # jacx[indok, 2*nc+kk] = (
                         # amp * 2*(lamb-(lamb0[ii]+dlamb))*bj/sigma**2 * expi
                    # )[indok]
            # jacx[:, -1] = 1.
            # return jacx/(std*phi.size)
    # return func, jac


def multigaussianfit2d(lamb, phi, data, std=None,
                       lamb0=None, forcelamb=None,
                       knots=None, deg=None, nbsplines=None,
                       x0=None, bounds=None,
                       method=None, max_nfev=None,
                       xtol=None, ftol=None, gtol=None,
                       loss=None, verbose=0, debug=None):
    """ Solve multi_gaussian fit in 2d from dlines and bsplines

    If Ti is True, all lines from the same ion have the same width
    If vi is True, all lines from the same ion have the same normalised shift
    If double is True, all lines are double with common shift and ratio

    Unknowns are:
        x = [bck, w0, v0, c00, c01, ..., c0n, w1, v1, c10, c11, ..., c1N, ...]

        - bck : constant background
        - wi  : spectral width of a group of lines (ion): wi^2 = 2kTi / m*c**2
                This way, it is dimensionless
        - vni : normalised velicity of the ion: vni = vi / c
        - cij : normalised coef (intensity) of line: cij = Aij

    Scaling is done so each quantity is close to unity:
        - bck: np.mean(data[data < mean(data)/2])
        - wi : Dlamb / 20
        - vni: 10 km/s
        - cij: np.mean(data)

    """

    # Check format
    if Ti is None:
        Ti = False
    if vi is None:
        vi = False
    if double is None:
        double = False
    assert isinstance(double, bool)
    if jac is None:
        jac = 'call'
    if method is None:
        method = 'trf'
    assert method in ['trf', 'dogbox'], method
    if xtol is None:
        xtol = 1.e-12
    if ftol is None:
        ftol = 1.e-12
    if gtol is None:
        gtol = 1.e-12
    if loss is None:
        loss = 'linear'
    if max_nfev is None:
        max_nfev = None

    if deg is None:
        deg = 3
    if nbsplines is None:
        nbsplines = 5

    # Prepare
    assert np.allclose(np.unique(lamb), lamb)
    assert np.allclose(np.unique(phi), phi)

    nlines = np.sum([v0['lamb'].size for v0 in dions.values()])

    # Get knots
    if knots is None:
        phimin, phimax = np.nanmin(phi), np.nanmax(phi)
        knots = np.linspace(phimin, phimax, nbsplines+1-deg)
    knots, nkperbs, nbs = get_knots_nbs_for_bsplines(np.unique(knots), deg)

    # Get indices
    dind, sizex, shapey0 = multigausfit2d_from_dlines_ind(
        dlines2=dlines2, double=double, Ti=Ti, vi=vi, nbs=nbs)

    # Get nbs spect1d for scaling
    for ii in range(nbs):
        pass

    # Get scaling
    if dscale is None:
        dscale = multigausfit1d_from_dlines_scale(data, lamb, phi)


    # --------------
    # Coming soon...

    # Get initial guess
    if x0_scale is None:
        x0_scale = multigausfit1d_from_dlines_x0(sizex, dind,
                                                 lines=lines, data=data,
                                                 lamb=lamb, dscale=dscale,
                                                 double=double)

    # get bounds
    if bounds_scale is None:
        bounds_scale = multigausfit1d_from_dlines_bounds(sizex, dind, double)

    # Get function, cost function and jacobian
    (func_detail, func,
     cost_scale, jac_scale) = multigausfit1d_from_dlines_funccostjac(
        data, lamb,
        dind=dind, dscale=dscale,
         lines=lines, shapey0=shapey0, double=double, jac=jac)


    # -------------------------------------
    # ------ Back-up ----------------------
    # -------------------------------------


    # Check inputs
    if std is None:
        std = 0.1*np.nanmean(data)

    # Scaling
    lambmin = np.nanmin(lamb)
    lamb0Delta = np.max(lamb0) - np.min(lamb0)
    nlamb0 = np.size(lamb0)
    nc = nbs*nlamb0

    dlambscale = lamb0Delta / nlamb0
    ampscale = np.nanmean(data) + np.nanstd(data)

    datascale = data / ampscale
    lambscale = lamb / dlambscale
    lamb0scale = lamb0 / dlambscale
    stdscale = std / ampscale

    # Get cost function and jacobian
    func, jac = get_multigaussianfit2d_costfunc(lamb=lambscale,
                                                phi=phi,
                                                data=datascale,
                                                std=stdscale,
                                                lamb0=lamb0scale,
                                                forcelamb=forcelamb,
                                                deg=deg, knots=knots,
                                                nlamb0=nlamb0, nbs=nbs,
                                                nkperbs=nkperbs, nc=nc,
                                                debug=debug)

    # Get initial guess
    if x0 is None:
        x0 = np.r_[np.ones((nc,)), np.ones((nc,))]
        if not forcelamb:
            x0 = np.r_[x0, np.zeros((nc,))]
            x0 = np.r_[x0, 0.]

    # Get bounds
    if bounds is None:
        bounds = (np.r_[np.zeros((nc,)),
                        np.full((nc,), nlamb0/100)],
                  np.r_[np.full((nc,), np.nanmax(data)/ampscale),
                        np.full((nc,), 3.)])
        if not forcelamb:
            bounds = (np.r_[bounds[0], -np.full((nc,), 2.)],
                      np.r_[bounds[1], np.full((nc,), 2.)])
        bounds = (np.r_[bounds[0], 0.],
                  np.r_[bounds[1], 0.1*np.nanmax(data)/ampscale])

    # Minimize
    res = scpopt.least_squares(func, x0, jac=jac, bounds=bounds,
                               method=method, ftol=ftol, xtol=xtol,
                               gtol=gtol, x_scale=1.0, f_scale=1.0, loss=loss,
                               diff_step=None, tr_solver=None,
                               tr_options={}, jac_sparsity=None,
                               max_nfev=max_nfev, verbose=verbose,
                               args=(), kwargs={})

    # Separate and reshape output
    camp = res.x[:nc].reshape((nlamb0, nbs)) * ampscale
    csigma = res.x[nc:2*nc].reshape((nlamb0, nbs)) * dlambscale
    if forcelamb:
        cdlamb = None
    else:
        cdlamb = res.x[2*nc:3*nc].reshape((nlamb0, nbs)) * dlambscale

    # Create output dict
    dout = {'camp': camp, 'csigma': csigma, 'cdlamb': cdlamb, 'bck':res.x[-1],
            'fit':(func(res.x)*stdscale*data.size + datascale) * ampscale,
            'lamb0':lamb0, 'knots': knots, 'deg':deg, 'nbsplines': nbsplines,
            'cost': res.cost, 'fun': res.fun, 'active_mask': res.active_mask,
            'nfev': res.nfev, 'njev': res.njev, 'status': res.status}
    return dout
