# coding: utf-8
from tofu_LauraBenchmarck_load_config import *
plt.ion()
out = load_config('B3')
out = load_config('A1')
out = load_config('A2')
out
out = load_config('B1')
out
baffle = out["Struct"]["Baffle"]
baffle
baffle.plot()
baffle.Poly
baffle.Poly = 0
baffle.geom
baffle.plot()
get_ipython().run_line_magic('pinfo', 'baffle.save')
baffle.plot_sino
baffle.plot_sino()
out = load_config('B1')
out2 = load_config('B1')
get_ipython().run_line_magic('edit', 'tofu_LauraBenchmarck_load_config.py')
import tofu as tf
get_ipython().run_line_magic('pinfo', 'tf.utils.create_CamLOS2D')
cam = tf.utils.create_CamLOS2D([3, 0, 0], 0.1, [0.1, 0.1], [100,100], nIn=[-1,0,0])
cam
get_ipython().set_next_input('Cam = tf.geom.LOSCam2D');get_ipython().run_line_magic('pinfo', 'tf.geom.LOSCam2D')
Cam = tf.geom.LOSCam2D(Id="Test", Du=cam, Ves=out["Ves"], Exp="West")
Cam = tf.geom.LOSCam2D(Id="Test", Du=cam, Ves=out["Ves"])
Cam.plot()
Cam.plot(Elt="L", EltVes="P")
Cam.plot_touch()
