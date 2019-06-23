# -*- coding: utf-8 -*-
"""
Created on Sat Jun  8 13:45:58 2019

@author: Arpan Khandelwal
email: napraarpan@gmail.com
"""

# Built-in
import os
from sys import stdout
from time import sleep

# Standard
import numpy as np

# More special
try:
    import cv2
except ImportError:
    print("Could not find opencv package. Try pip intall opencv-contrib-python")
    
def rm_back(im_path, w_dir, shot_name, rate = None,
            im_out = None, meta_data = None, verb = True):
    """
    This subroutine removes background from a collection of images
    It follows frame by frame subtraction where the previous frame is 
    subtracted from the successive frame
    The images are read in original form i.e., without any modifications
    For more information consult:
    
    1. https://docs.opencv.org/3.4/dd/d4d/tutorial_js_image_arithmetics.html
    2. https://docs.opencv.org/3.1.0/d1/dc5/tutorial_background_subtraction.html
    3. https://docs.opencv.org/3.3.0/db/d5c/tutorial_py_bg_subtraction.html
    
    Among the parameters present, if used as a part of dumpro, 
    w_dir, shot_name, rate and meta_data are provided by the image processing 
    class in the core file.
    The verb paramenter is used when this subroutine is used independently.
    Otherwise it is suppressed by the core class.
    
    
    Parameters
    -----------------------
    im_path:          string
     input path where the images are stored
    w_dir:            string
     A working directory where the proccesed images are stored
    shot_name:        String
     The name of the tokomak machine and the shot number. Generally
     follows the nomenclature followed by the lab
    rate:             integer
     if rate = 0 then a guassian mixture based background/foreground 
     segmentation algorithm is used and if rate = 1 then it is a slow camera 
     and the method of background removal will be frame by frame subtraction  
     By default rate is set at zero. Some information loss happens in the frame
     by frame subtraction is used but we get more false positives for 
     the guassian based method
    meta_data:        dictionary
     A dictionary containing all the video meta_data. By default it is None
     But if the user inputs some keys into the dictionary, the code will use 
     the information from the dictionary and fill in the missing gaps if
     required
     meta_data has information on total number of frames, demension, fps and 
     the four character code of the video
    
    Return
    -----------------------
    im_out:              String
     Path along where the proccessed images are stored  
    meta_data:        dictionary
     A dictionary containing the meta data of the video.
    """
    if rate == None:
        rate = 0
    if verb == True:
        print('###########################################')
        print('Background Removal')
        print('###########################################\n')
    #reading the output directory
    if verb == True:
        print('Creating output directory ...')
    #default output folder name
    folder = shot_name + '_frground'
    #creating the output directory
    if im_out == None:
        im_out = os.path.join(w_dir, folder, '')
        if not os.path.exists(im_out):
            #creating output directory using w_dir and shot_name
            os.mkdir(im_out)
    
    if verb == True:
        print('output directory is : ', im_out,'\n')
    
    #describing an empty list that will later contain all the frames
    #frame_array = []
    #creating a list of all the files
    files = [f for f in os.listdir(im_path) if os.path.isfile(os.path.join(im_path,f))]    
    
    #sorting files according to names using lambda function
    files.sort(key = lambda x: int(x[5:-4]))
    #looping throuah all the file names in the list and converting them to image path
    
    if verb == True:
        print('subtracting background...')
        print('Reading the image files ...')
        print('Files processing...')
    
    #background subtractor method
    back = cv2.bgsegm.createBackgroundSubtractorMOG()
    
    #looping through the video
    f_count = 1
    for i in range(len(files)-1):
        #converting to path
        f_name1 = im_path + files[i]
        f_name2 = im_path + files[i+1]
        #dynamic printing
        if verb == True:
            stdout.write("\r[%s/%s]" % (f_count, len(files)))
            stdout.flush()   
        if rate == 0:
            #reading each file to extract its meta_data
            img1 = cv2.imread(f_name1,cv2.IMREAD_UNCHANGED)
            #removing backgroud
            dst = back.apply(img1)
        elif rate == 1:
            img1 = cv2.imread(f_name1,cv2.IMREAD_UNCHANGED)
            img2 = cv2.imread(f_name2,cv2.IMREAD_UNCHANGED)
            #performing frame by frame subtraction
            dst = cv2.subtract(img1, img2)

        #generic name of each image
        name = im_out + 'frame' + str(f_count) + '.jpg'
        #writting the output file
        cv2.imwrite(name, dst)
        #image meta_data
        height,width = dst.shape[0],dst.shape[1]
        size = (height, width)
        #providing information to user
        f_count += 1
    
    #dynamic printing
    stdout.write("\n")
    stdout.flush()
    if verb == True:
        print('background subtraction successfull...')
    #frame_array.append(dst)
    
    if verb == True:
        print('Reading meta_data...')
        
    if meta_data == None:
        #defining the four character code
        fourcc = cv2.VideoWriter_fourcc(*'MJPG')
        #defining the frame dimensions
        frame_width = width
        frame_height = height
        #defining the fps
        fps = 25
        #defining the total number of frames
        N_frames = len(files)
        #defining the meta_data dictionary
        meta_data = {'fps' : fps, 'frame_height' : frame_height, 
                     'frame_width' : frame_width, 'fourcc' : fourcc,
                     'N_frames' : N_frames}
    else:
        #describing the four character code      

        fourcc = meta_data.get('fourcc', cv2.VideoWriter_fourcc(*'MJPG'))
        if 'fourcc' not in meta_data:
            meta_data['fourcc'] = fourcc
        
        #describing the frame width
        frame_width = meta_data.get('frame_width', width)
        if 'frame_width' not in meta_data:
            meta_data['frame_width'] = frame_width
        
        #describing the frame height
        frame_height = meta_data.get('frame_height', height)
        if 'frame_height' not in meta_data:
            meta_data['frame_height'] = frame_height
            
        #describing the speed of the video in frames per second 
        fps = meta_data.get('fps', 25)
        if 'fps' not in meta_data:
            meta_data['fps'] = fps

        #describing the total number of frames in the video
        N_frames = meta_data.get('N_frames', len(files))
        if 'N_frames' not in meta_data:
            meta_data['N_frames'] = N_frames
            
        if verb == True:
            print('meta_data read successfully...\n')
    
    return im_out, meta_data