"""
This module contains tests for tofu.geom in its structured version
"""

# External modules
import os
import itertools as itt
import numpy as np
import matplotlib.pyplot as plt
import warnings as warn

# Importing package tofu.gem
import tofu as tf
from tofu import __version__
import tofu.defaults as tfd
import tofu.utils as tfu
import tofu.geom as tfg


_here = os.path.abspath(os.path.dirname(__file__))
VerbHead = 'tofu.geom.test_04_core_optics'
keyVers = 'Vers'
_Exp = 'WEST'


#######################################################
#
#     Setup and Teardown
#
#######################################################

def setup_module(module):
    print("") # this is to get a newline after the dots
    lf = os.listdir(_here)
    lf = [f for f in lf
         if all([s in f for s in ['TFG_',_Exp,'.npz']])]
    lF = []
    for f in lf:
        ff = f.split('_')
        v = [fff[len(keyVers):] for fff in ff
             if fff[:len(keyVers)]==keyVers]
        msg = f + "\n    "+str(ff) + "\n    " + str(v)
        assert len(v)==1, msg
        v = v[0]
        if '.npz' in v:
            v = v[:v.index('.npz')]
        # print(v, __version__)
        if v!=__version__:
            lF.append(f)
    if len(lF)>0:
        print("Removing the following previous test files:")
        for f in lF:
            os.remove(os.path.join(_here,f))
        #print("setup_module before anything in this file")

def teardown_module(module):
    #os.remove(VesTor.Id.SavePath + VesTor.Id.SaveName + '.npz')
    #os.remove(VesLin.Id.SavePath + VesLin.Id.SaveName + '.npz')
    #print("teardown_module after everything in this file")
    #print("") # this is to get a newline
    lf = os.listdir(_here)
    lf = [f for f in lf
         if all([s in f for s in ['TFG_',_Exp,'.npz']])]
    lF = []
    for f in lf:
        ff = f.split('_')
        v = [fff[len(keyVers):] for fff in ff
             if fff[:len(keyVers)]==keyVers]
        msg = f + "\n    "+str(ff) + "\n    " + str(v)
        assert len(v)==1, msg
        v = v[0]
        if '.npz' in v:
            v = v[:v.index('.npz')]
        # print(v, __version__)
        if v==__version__:
            lF.append(f)
    if len(lF)>0:
        print("Removing the following test files:")
        for f in lF:
            os.remove(os.path.join(_here,f))


#######################################################
#
#   Crystal class
#
#######################################################

class Test01_Crystal(object):

    @classmethod
    def setup_class(cls, verb=False):
        #print ("")
        #print "--------- "+VerbHead+cls.__name__

        # Prepare input
        dgeom = {
            'Type': 'sph',
            'Typeoutline': 'rect',
            'summit': np.array([ 4.6497750e-01, -8.8277925e+00,  3.5125000e-03]),
            'center': np.array([ 1.560921  , -6.31106476,  0.00729429]),
            'extenthalf': np.array([0.01457195, 0.01821494]),
            'rcurve': 2.745,
            'move': 'rotate_around_3daxis',
            'move_param': 0.022889993139905633,
            'move_kwdargs': {
                'axis': np.array([[ 4.95e-01, -8.95e+00, -8.63e-02],
                               [-1.37e-04, -2.18e-03,  9.99e-01]])
            }
        }
        dmat = {
            'formula': 'Quartz',
             'density': 2.6576,
             'symmetry': 'hexagonal',
             'lengths': np.array([4.9079e-10, 4.9079e-10, 5.3991e-10]),
             'angles': np.array([1.57079633, 1.57079633, 2.0943951 ]),
             'cut': np.array([ 1,  1, -2,  0]),
             'd': 2.4539499999999996e-10,
        }
        dbragg = {
            'lambref': 3.96e-10,
        }

        dmat1 = dict(dmat)
        dmat2 = dict(dmat)
        dmat3 = dict(dmat)

        # cryst1
        cryst1 = tfg.CrystalBragg(
            dgeom=dgeom,
            dmat=dmat1,
            dbragg=dbragg,
            Name='Cryst1',
            Diag='SpectrX2D',
            Exp='WEST',
        )

        # cryst2
        dmat2['alpha'] = 0.
        dmat2['beta'] = 0.
        cryst2 = tfg.CrystalBragg(
            dgeom=dgeom,
            dmat=dmat2,
            dbragg=dbragg,
            Name='Cryst2',
            Diag='SpectrX2D',
            Exp='WEST',
        )

        # cryst3
        dmat3['alpha'] = (3/60)*np.pi/180
        dmat3['beta'] = 0.
        cryst3 = tfg.CrystalBragg(
            dgeom=dgeom,
            dmat=dmat3,
            dbragg=dbragg,
            Name='Cryst3',
            Diag='SpectrX2D',
            Exp='WEST',
        )

        # cryst4
        dmat['alpha'] = (3/60)*np.pi/180
        dmat['beta'] = np.pi/1000.
        cryst4 = tfg.CrystalBragg(
            dgeom=dgeom,
            dmat=dmat,
            dbragg=dbragg,
            Name='Cryst4',
            Diag='SpectrX2D',
            Exp='WEST',
        )

        cls.dobj = {
            'cryst1': cryst1,
            'cryst2': cryst2,
            'cryst3': cryst3,
            'cryst4': cryst4,
        }


    @classmethod
    def teardown_class(cls):
        #print ("teardown_class() after any methods in this class")
        pass
        # for typ in cls.dobj.keys():
            # for c in cls.dobj[typ].keys():
                # for f in cls.dlpfe[typ][c]:
                    # try:
                        # os.remove(f)
                    # except Exception as err:
                        # msg = str(err)
                        # msg += '\n\n'+str(f)
                        # raise Exception(msg)

    def setup(self):
        #print ("TestUM:setup() before each test method")
        pass

    def teardown(self):
        #print ("TestUM:teardown() after each test method")
        pass

    # def test00_todo(self):
        # pass

    def test01_todict(self):
        for k0 in self.dobj.keys():
            dd = self.dobj[k0].to_dict()
            assert type(dd) is dict

    def test02_fromdict(self):
        for k0 in self.dobj.keys():
            dd = self.dobj[k0].to_dict()
            obj = tfg.CrystalBragg(fromdict=dd)
            assert isinstance(obj, self.dobj[k0].__class__)

    def test03_copy_equal(self):
        for k0 in self.dobj.keys():
            obj = self.dobj[k0].copy()
            assert obj == self.dobj[k0]
            assert not  obj != self.dobj[k0]

    def test04_get_nbytes(self):
        for k0 in self.dobj.keys():
            nb, dnb = self.dobj[k0].get_nbytes()

    def test05_strip_nbytes(self, verb=False):
        lok = tfg.CrystalBragg._dstrip['allowed']
        nb = np.full((len(lok),), np.nan)
        for k0, obj in self.dobj.items():
            for ii in lok:
                obj.strip(ii)
                nb[ii] = obj.get_nbytes()[0]
            assert np.all(np.diff(nb)<=0.)
            for ii in lok[::-1]:
                obj.strip(ii)

    def test06_set_move_None(self):
        pass

    def test07_rotate_copy(self):
        pass
        # for typ in self.dobj.keys():
            # if typ == 'Lin':
                # continue
            # dkwd0 = dict(axis_rz=[2.4, 0], angle=np.pi/4,
                         # return_copy=True)
            # for c in self.dobj[typ].keys():
                # obj = getattr(self.dobj[typ][c],
                              # 'rotate_in_cross_section')(**dkwd0)

    def test08_get_detector_approx(self):
        for k0, obj in self.dobj.items():
            det0 = obj.get_detector_approx(use_non_parallelism=False)
            det1 = obj.get_detector_approx(use_non_parallelism=True)
            assert isinstance(det0, dict) and isinstance(det0, dict)
            lk = ['nout', 'ei']
            assert all([ss in det0.keys() for ss in lk])
            assert all([ss in det1.keys() for ss in lk])
            if k0 in ['cryst1', 'cryst2']:
                assert all([
                    np.allclose(det0[kk], det1[kk])
                    for kk in lk
                ])
            elif k0 in ['cryst3', 'cryst4']:
                assert not any([
                    np.allclose(det0[kk], det1[kk])
                    for kk in lk
                ])
                for k1, v1 in det0.items():
                    assert np.linalg.norm(v1 - det1[k1]) <= 0.01

    def test12_plot(self):
        for k0, obj in self.dobj.items():
            det = obj.get_detector_approx()
            dax = obj.plot()
            dax = obj.plot(det=det, element='scvr')
        plt.close('all')

    def test15_saveload(self, verb=False):
        for k0, obj in self.dobj.items():
            obj.strip(-1)
            pfe = obj.save(verb=verb, return_pfe=True)
            obj2 = tf.load(pfe, verb=verb)
            msg = "Unequal saved / loaded objects !"
            assert obj2 == obj, msg
            # Just to check the loaded version works fine
            obj2.strip(0)
            os.remove(pfe)