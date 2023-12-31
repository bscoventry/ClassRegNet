#!/usr/bin/env python

##  noisy_object_detection_and_localization.py

#-------------------------------------------------------------------------------------------------------------------
# Author: Brandon S Coventry               Purdue University Weldon School of BME
# Purpose: Generate Cortex net for hw05 of deep learning. See description
# Date: 4/1/2020
# Revision History: Inital coding 4/3/2020
# Description: Generally, this network models the central auditory pathway (CAP) of the nervous system. The CAP has
# a direct pathway known as the lemniscal pathway, consisting of projections of cochlear nucleus (CN) to inferior
# colliculus (IC) to medial geniculate body of the auditory thalamus (MGB) to auditory cortex (A1). Each pathway
# is marked by changes in neural coding and detection in noise. The nonlemniscal pathway consists of the superior
# olivary complex (SOC) and lateral lemniscus (LL). The SOC in sound is a feature detector, detecting binaural 
# stimuli. Here I model it as more specific feature detection. The LL is a feedback mechanism. The IC is the major 
# integrative hub, so I use this to pool all features from afferent layers. The MGB is a major source of coding transformation,
# where fine features are fully integrated and detected. The auditory cortex acts in a population coding method.

# This homework assignment starts by using but modifying the noisy_object_detection_and_localization file found in DLStudio.
# Credit for this code framework belongs to Dr. Kak. I used this as a basis for network development and mostly used it for
# its dataloaders on the Purdue5 dataset and its training algorithm. In using F.conv2d, I used ideas from the Pytorch forum,
# listed in inline comments, along with link to the website.

# For edgenet, it dawned on me that sensory systems tend to use pathways which split the sensory stimulus into different
# components passed along parallel pathways. Following this idea, I developed a network which first split the image
# into 3 grayscale level images. One image is smoothed via Gaussian Smoothing, the next image is convolved with a sobel kernel
# in the X direction, with the last layer convolved with a sobel kernel in the Y direction. These are then pooled and passed
# through a net of increasing complexity, sharing a shrinking Average Pooling Layer which I got inspiration from the VGG16
# though this net was built by me. 
# 
# #This task uses a slightly less complicated net than task 4, but as we shall see, the less complicated net seems
#  to perform a little bit better than the more complicated net on this task. 
#
# Note, using kernels in F.conv2d was figured out with help from answers in PyTorch forum. These were not my questions,
# but gave me the context I needed to implement: https://discuss.pytorch.org/t/is-there-anyway-to-do-gaussian-filtering-for-an-image-2d-3d-in-pytorch/12351 and
# https://discuss.pytorch.org/t/setting-custom-kernel-for-cnn-in-pytorch/27176
# For Tasks 2,4 each dataset was loaded seperately and run.
#-------------------------------------------------------------------------------------------------------------------
#from cortexNet1 import cortexNet
import random
import numpy
import torch
import os, sys
import pdb
import torchvision
from scipy.ndimage.filters import gaussian_filter
class EdgeNet(torch.nn.Module):
    #     #Class draws influence from VGG16 (K. Simonyan and A. Zisserman) but is quite distinct from it.
#     #Models information and noise resolution in the central auditory system
    def __init__(self,inChannels,numOutputs,numRegOutputs,edgeDetect = 1):
        super(EdgeNet, self).__init__()
        self.inChannels = inChannels           #Image dimensionality subject to preprocessing
        self.numOutputs = numOutputs         #Output classification dimensionality. 
        self.numRegOutputs = numRegOutputs
        self.edgeDetect = edgeDetect
        self.sobelKernelX = torch.tensor([[1.,0.,-1.],[2.,0.,-2.],[1.,0.,-1.]])
        self.sobelKernelX = self.sobelKernelX.view(1,1,3,3).repeat(1,1,1,1) #How to use custom kernels in pytorch was found at the following PyTorch forum answer: https://discuss.pytorch.org/t/setting-custom-kernel-for-cnn-in-pytorch/27176
        self.sobelKernelY = torch.tensor([[1.,2.,1.],[0.,0.,0.],[-1.,-2.,-1.]])
        self.sobelKernelY = self.sobelKernelY.view(1,1,3,3).repeat(1,1,1,1)
        #Gauss Kernel Generated by me in Matlab and transfered here
        self.device = torch.device("cuda:0")
        self.gaussKernel = torch.tensor([[0,	0,	0,	0,	0,	0,	0,	0,	0,	0,	0,	0,	0,	0,	0],
        [0,	0,	0,	0,	0,	0,	0,	0,	0,	0,	0,	0,	0,	0,	0],
        [0,	0,	0,	0,	0,	0,	0,	0,	0,	0,	0,	0,	0,	0,	0],
        [0,	0,	0,	0,	0,	0.000106542709594868,	0.000301935253041011,	0.000427277986095659,	0.000301935253041011,	0.000106542709594868,	0,	0,	0,	0,	0],
        [0,	0,	0,	0,	0.000213362026585964,	0.00121087859827493,	0.00343155282386115,	0.00485609734203881,	0.00343155282386115,	0.00121087859827493,	0.000213362026585964,	0,	0,	0,	0],
        [0,	0,	0,	0.000106542709594868,	0.00121087859827493,	0.00687201468425086,	0.0194748519207060,	0.0275594698677342,	0.0194748519207060,	0.00687201468425086,	0.00121087859827493,	0.000106542709594868,	0,	0,	0],
        [0,	0,	0,	0.000301935253041011,	0.00343155282386115,	0.0194748519207060,	0.0551904899450562,	0.0781017822789753,	0.0551904899450562,	0.0194748519207060,	0.00343155282386115,	0.000301935253041011,	0,	0,	0],
        [0,	0,	0,	0.000427277986095659,	0.00485609734203881,	0.0275594698677342,	0.0781017822789753,	0.110524266068757,	0.0781017822789753,	0.0275594698677342,	0.00485609734203881,	0.000427277986095659,	0,	0,	0],
        [0,	0,	0,	0.000301935253041011,	0.00343155282386115,	0.0194748519207060,	0.0551904899450562,	0.0781017822789753,	0.0551904899450562,	0.0194748519207060,	0.00343155282386115,	0.000301935253041011,	0,	0,	0],
        [0,	0,	0,	0.000106542709594868,	0.00121087859827493,	0.00687201468425086,	0.0194748519207060,	0.0275594698677342,	0.0194748519207060,	0.00687201468425086,	0.00121087859827493,	0.000106542709594868,	0,	0,	0],
        [0,	0,	0,	0.000213362026585964,	0.00121087859827493,	0.00343155282386115,	0.00485609734203881,	0.00343155282386115,	0.00121087859827493,	0.000213362026585964,	0,	0,	0,	0,0],
        [0, 0,	0,	0,	0,	0.000106542709594868,	0.000301935253041011,	0.000427277986095659,	0.000301935253041011,	0.000106542709594868,	0,	0,	0,	0,	0],
        [0,	0,	0,	0,	0,	0,	0,	0,	0,	0,	0,	0,	0,	0,	0],
        [0,	0,	0,	0,	0,	0,	0,	0,	0,	0,	0,	0,	0,	0,	0],
        [0,	0,	0,	0,	0,	0,	0,	0,	0,	0,	0,	0,	0,	0,	0]])
        self.gaussFilter = self.gaussKernel.view(1,1,15,15).repeat(1,1,1,1)
        self.gaussFilterNoGPU = self.gaussFilter
        self.gaussFilter = self.gaussFilter.to(self.device)
        self.sobelKernelX = self.sobelKernelX.to(self.device)
        self.sobelKernelY = self.sobelKernelY.to(self.device)
        self.grayTransforms = torchvision.transforms.Compose(
            [torchvision.transforms.Grayscale(num_output_channels=3)]
        )
        self.averagePoolClass = torch.nn.AdaptiveAvgPool2d((7, 7))
        self.averagePoolR = torch.nn.AdaptiveAvgPool2d((7, 7))
        #Now define the network
        self.firstConvLayerSmoothClass = torch.nn.Sequential(
            torch.nn.Conv2d(3,64,kernel_size = 3, padding = 1),
            torch.nn.BatchNorm2d(64),
            torch.nn.ReLU(inplace = True)
        )
        self.secondConvLayerSmoothClass = torch.nn.Sequential(
            torch.nn.Conv2d(64,64,kernel_size = 3, padding = 1),
            torch.nn.BatchNorm2d(64),
            torch.nn.ReLU(inplace = True),
            torch.nn.Conv2d(64,128,kernel_size = 3, padding = 1),
            torch.nn.BatchNorm2d(128),
            torch.nn.ReLU(inplace = True),
            torch.nn.Conv2d(128,128,kernel_size = 3, padding = 1),
            torch.nn.BatchNorm2d(128),
            torch.nn.ReLU(inplace = True),
        )
        self.thirdConvLayerSmoothClass = torch.nn.Sequential(
            torch.nn.MaxPool2d(kernel_size = 2,stride = 2),
            torch.nn.Conv2d(128,256,kernel_size = 3, padding = 1),
            torch.nn.BatchNorm2d(256),
            torch.nn.ReLU(inplace = True),
            torch.nn.Conv2d(256,256,kernel_size = 3, padding = 1),
            torch.nn.BatchNorm2d(256),
            torch.nn.ReLU(inplace = True),
        )
        self.fourthConvLayerSmoothClass = torch.nn.Sequential(
            torch.nn.Conv2d(256,256,kernel_size = 3, padding = 1),
            torch.nn.BatchNorm2d(256),
            torch.nn.ReLU(inplace = True),
            torch.nn.Conv2d(256,256,kernel_size = 3, padding = 1),
            torch.nn.BatchNorm2d(256),
            torch.nn.ReLU(inplace = True),
        )
        self.fifthConvLayerSmoothClass = torch.nn.Sequential(
            torch.nn.MaxPool2d(kernel_size = 2,stride = 2),
            torch.nn.Conv2d(256,512,kernel_size = 3, padding = 1),
            torch.nn.BatchNorm2d(512),
            torch.nn.ReLU(inplace = True),
            torch.nn.Conv2d(512,512,kernel_size = 3, padding = 1),
            torch.nn.BatchNorm2d(512),
            torch.nn.ReLU(inplace = True),
        )
        self.sixthConvLayerSmoothClass = torch.nn.Sequential(
            torch.nn.MaxPool2d(kernel_size = 2,stride = 2),
            torch.nn.Conv2d(512,512,kernel_size = 3, padding = 1),
            torch.nn.BatchNorm2d(512),
            torch.nn.ReLU(inplace = True),
            torch.nn.Conv2d(512,512,kernel_size = 3, padding = 1),
            torch.nn.BatchNorm2d(512),
            torch.nn.ReLU(inplace = True),
        )
        self.seventhConvLayerSmoothClass = torch.nn.Sequential(
            torch.nn.MaxPool2d(kernel_size = 2,stride = 2),
            torch.nn.Conv2d(512,1024,kernel_size = 3, padding = 1),
            torch.nn.BatchNorm2d(1024),
            torch.nn.ReLU(inplace = True),
            torch.nn.Conv2d(1024,1024,kernel_size = 3, padding = 1),
            torch.nn.BatchNorm2d(1024),
            torch.nn.ReLU(inplace = True),
        )

        self.eigthConvLayerSmoothClass = torch.nn.Sequential(
            #torch.nn.MaxPool2d(kernel_size = 2,stride = 2),
            torch.nn.Conv2d(1024,1024,kernel_size = 3, padding = 1),
            torch.nn.BatchNorm2d(1024),
            torch.nn.ReLU(inplace = True),
            torch.nn.Conv2d(1024,1024,kernel_size = 3, padding = 1),
            torch.nn.BatchNorm2d(1024),
            torch.nn.ReLU(inplace = True),
        )
        self.fullConClass = torch.nn.Sequential(
            torch.nn.Linear(1024*7*7,4096),
            torch.nn.ReLU(inplace = True),
            torch.nn.Dropout(),
            torch.nn.Linear(4096,1000),
            torch.nn.ReLU(inplace = True),
            torch.nn.Dropout(),
            torch.nn.Linear(1000,numOutputs)
        )
        self.skipBatchNorm1 = torch.nn.BatchNorm2d(128)
        self.skipConv1 = torch.nn.Conv2d(128,128,kernel_size = 3,padding = 1)
        self.skipBatchNorm2 = torch.nn.BatchNorm2d(256)
        self.skipConv2 = torch.nn.Conv2d(256,256,kernel_size = 3,padding = 1)
        self.skipBatchNorm3 = torch.nn.BatchNorm2d(512)
        self.skipConv3 = torch.nn.Conv2d(512,512,kernel_size = 3,padding = 1)
        self.skipBatchNorm4 = torch.nn.BatchNorm2d(1024)
        self.skipConv4 = torch.nn.Conv2d(1024,1024,kernel_size = 3,padding = 1)
        self.skipBatchNorm1R = torch.nn.BatchNorm2d(128)
        self.skipConv1R = torch.nn.Conv2d(128,128,kernel_size = 3,padding = 1)
        self.skipBatchNorm2R = torch.nn.BatchNorm2d(256)
        self.skipConv2R = torch.nn.Conv2d(256,256,kernel_size = 3,padding = 1)
        self.skipBatchNorm3R = torch.nn.BatchNorm2d(512)
        self.skipConv3R = torch.nn.Conv2d(512,512,kernel_size = 3,padding = 1)
        self.skipBatchNorm4R = torch.nn.BatchNorm2d(1024)
        self.skipConv4R = torch.nn.Conv2d(1024,1024,kernel_size = 3,padding = 1)

        self.firstConvLayerSmoothR = torch.nn.Sequential(
            torch.nn.Conv2d(3,64,kernel_size = 3, padding = 1),
            torch.nn.BatchNorm2d(64),
            torch.nn.ReLU(inplace = True)
        )
        self.secondConvLayerSmoothR = torch.nn.Sequential(
            torch.nn.Conv2d(64,64,kernel_size = 3, padding = 1),
            torch.nn.BatchNorm2d(64),
            torch.nn.ReLU(inplace = True),
            torch.nn.Conv2d(64,128,kernel_size = 3, padding = 1),
            torch.nn.BatchNorm2d(128),
            torch.nn.ReLU(inplace = True),
            torch.nn.Conv2d(128,128,kernel_size = 3, padding = 1),
            torch.nn.BatchNorm2d(128),
            torch.nn.ReLU(inplace = True),
        )
        self.thirdConvLayerSmoothR = torch.nn.Sequential(
            torch.nn.MaxPool2d(kernel_size = 2,stride = 2),
            torch.nn.Conv2d(128,256,kernel_size = 3, padding = 1),
            torch.nn.BatchNorm2d(256),
            torch.nn.ReLU(inplace = True),
            torch.nn.Conv2d(256,256,kernel_size = 3, padding = 1),
            torch.nn.BatchNorm2d(256),
            torch.nn.ReLU(inplace = True),
        )
        self.fourthConvLayerSmoothR = torch.nn.Sequential(
            torch.nn.Conv2d(256,256,kernel_size = 3, padding = 1),
            torch.nn.BatchNorm2d(256),
            torch.nn.ReLU(inplace = True),
            torch.nn.Conv2d(256,256,kernel_size = 3, padding = 1),
            torch.nn.BatchNorm2d(256),
            torch.nn.ReLU(inplace = True),
        )
        self.fifthConvLayerSmoothR = torch.nn.Sequential(
            torch.nn.MaxPool2d(kernel_size = 2,stride = 2),
            torch.nn.Conv2d(256,512,kernel_size = 3, padding = 1),
            torch.nn.BatchNorm2d(512),
            torch.nn.ReLU(inplace = True),
            torch.nn.Conv2d(512,512,kernel_size = 3, padding = 1),
            torch.nn.BatchNorm2d(512),
            torch.nn.ReLU(inplace = True),
        )
        self.sixthConvLayerSmoothR = torch.nn.Sequential(
            #torch.nn.MaxPool2d(kernel_size = 2,stride = 2),
            torch.nn.Conv2d(512,512,kernel_size = 3, padding = 1),
            torch.nn.BatchNorm2d(512),
            torch.nn.ReLU(inplace = True),
            torch.nn.Conv2d(512,512,kernel_size = 3, padding = 1),
            torch.nn.BatchNorm2d(512),
            torch.nn.ReLU(inplace = True),
        )
        self.seventhConvLayerSmoothR = torch.nn.Sequential(
            torch.nn.MaxPool2d(kernel_size = 2,stride = 2),
            torch.nn.Conv2d(512,1024,kernel_size = 3, padding = 1),
            torch.nn.BatchNorm2d(1024),
            torch.nn.ReLU(inplace = True),
            torch.nn.Conv2d(1024,1024,kernel_size = 3, padding = 1),
            torch.nn.BatchNorm2d(1024),
            torch.nn.ReLU(inplace = True),
        )

        self.eigthConvLayerSmoothR = torch.nn.Sequential(
            #torch.nn.MaxPool2d(kernel_size = 2,stride = 2),
            torch.nn.Conv2d(1024,1024,kernel_size = 3, padding = 1),
            torch.nn.BatchNorm2d(1024),
            torch.nn.ReLU(inplace = True),
            torch.nn.Conv2d(1024,1024,kernel_size = 3, padding = 1),
            torch.nn.BatchNorm2d(1024),
            torch.nn.ReLU(inplace = True),
        )
        self.fullConR = torch.nn.Sequential(
            torch.nn.Linear(1024*7*7,4096),
            torch.nn.ReLU(inplace = True),
            torch.nn.Dropout(),
            torch.nn.Linear(4096,512),
            torch.nn.ReLU(inplace = True),
            torch.nn.Dropout(),
            #torch.nn.Linear(1024,512),
            #torch.nn.ReLU(inplace = True),
            #torch.nn.Dropout(),
            torch.nn.Linear(512,4)
        )
    def splitMetrics(self,x):
        x = torch.split(x,1,1)     #Get individual RGB to due a pseudo-grayscale for edge detection
        x0 = x[0]
        x1 = x[0]
        x2 = x[0]     #Will recombine after networks run in parallel
        
        return x0,x1,x2 
        # toTransform = x
        # imgVals = torchvision.transforms.functional.to_pil_image(toTransform[0])
        # grayScaleVals = torchvision.transforms.functional.to_grayscale(imgVals,3)
        # x[0] = torchvision.transforms.functional.to_tensor(grayScaleVals)
    def forward(self,x):
        x0,x1,x2 = self.splitMetrics(x)
        #Weird issue with conv2d, temp fix for now.
        x0 = x0.to(self.device)
        x1 = x1.to(self.device)
        x2 = x2.to(self.device)
        if x0.type() != torch.cuda.FloatTensor:
            #Use of F.conv2d instead of nn.Conv2d was found: https://discuss.pytorch.org/t/setting-custom-kernel-for-cnn-in-pytorch/27176
            x0Class = torch.nn.functional.conv2d(x0,self.gaussFilter,bias=None, padding=7 )     #Blurring Step with Gaussian Kernals.
            x1Class = torch.nn.functional.conv2d(x1,self.sobelKernelX,bias=None,padding = 1)
            x2Class = torch.nn.functional.conv2d(x2,self.sobelKernelY,bias=None,padding=1)
            x0R = x0Class
            x1R = x1Class
            x2R = x2Class
        else:
            x0Class = torch.nn.functional.conv2d(x0,self.gaussFilter,bias=None, padding=7 ) 
            x1Class = torch.nn.functional.conv2d(x1,self.sobelKernelX,bias=None,padding = 1)
            x2Class = torch.nn.functional.conv2d(x2,self.sobelKernelY,bias=None,padding=1)
            x0R = x0Class
            x1R = x1Class
            x2R = x2Class
        x0Class = torch.cat((x0Class,x1Class,x2Class),dim=1)
        x0R = torch.cat((x0R,x1R,x2R),dim=1)
        x0Class = self.firstConvLayerSmoothClass(x0Class)
        x0Class = self.secondConvLayerSmoothClass(x0Class)
        addLayer1 = x0Class
        x0Class = torch.nn.functional.relu(self.skipBatchNorm1(self.skipConv1(x0Class)))
        x0Class = torch.add(x0Class,addLayer1)
        x0Class = self.thirdConvLayerSmoothClass(x0Class)
        addLayer = x0Class
        x0Class = torch.nn.functional.relu(self.skipBatchNorm2(self.skipConv2(x0Class)))
        x0Class = torch.add(x0Class,addLayer)
        x0Class = self.fourthConvLayerSmoothClass(x0Class)
        x0Class = self.fifthConvLayerSmoothClass(x0Class)
        addLayer = x0Class
        x0Class = torch.nn.functional.relu(self.skipBatchNorm3(self.skipConv3(x0Class)))
        x0Class = torch.add(x0Class,addLayer)
        x0Class = self.sixthConvLayerSmoothClass(x0Class)
        x0Class = self.seventhConvLayerSmoothClass(x0Class)
        addLayer = x0Class
        x0Class = torch.nn.functional.relu(self.skipBatchNorm4(self.skipConv4(x0Class)))
        x0Class = torch.add(x0Class,addLayer)
        x0Class = self.eigthConvLayerSmoothClass(x0Class)

        #x0R = torch.nn.functional.conv2d(x0R,self.gaussFilter,bias=None, padding=1 ) 
        x0R = self.firstConvLayerSmoothR(x0R)
        x0R = self.secondConvLayerSmoothR(x0R)
        addLayer = x0R
        x0R = torch.nn.functional.relu(self.skipBatchNorm1R(self.skipConv1R(x0R)))
        x0R = torch.add(x0R,addLayer)
        x0R = self.thirdConvLayerSmoothR(x0R)
        addLayer = x0R
        x0R = torch.nn.functional.relu(self.skipBatchNorm2R(self.skipConv2R(x0R)))
        x0R = torch.add(x0R,addLayer)
        x0R = self.fourthConvLayerSmoothR(x0R)
        x0R = self.fifthConvLayerSmoothR(x0R)
        addLayer = x0R
        x0R = torch.nn.functional.relu(self.skipBatchNorm3R(self.skipConv3R(x0R)))
        x0R = torch.add(x0R,addLayer)
        x0R = self.sixthConvLayerSmoothR(x0R)
        x0R = self.seventhConvLayerSmoothR(x0R)
        addLayer = x0R
        x0R = torch.nn.functional.relu(self.skipBatchNorm4R(self.skipConv4R(x0R)))
        x0R = torch.add(x0R,addLayer)
        x0R = self.eigthConvLayerSmoothR(x0R)

        if self.edgeDetect == 0:
            x0Class = self.averagePoolClass(x0Class)
            xsizes = x0Class.size()
            x0Class = x0Class.view(-1,xsizes[1]*xsizes[2]*xsizes[3])
            x0Class = torch.flatten(x0Class,1)          #Prepare for Linear Auditory Cortex Layers
            x0Class = self.fullConClass(x0Class)
            x0R = self.averagePoolClass(x0R)
            xsizes = x0R.size()
            x0R = x0R.view(-1,xsizes[1]*xsizes[2]*xsizes[3])
            x0R = torch.flatten(x0R,1)          #Prepare for Linear Auditory Cortex Layers
            x0R = self.fullConR(x0R)
            return x0Class,x0R


if __name__ == '__main__':
    torch.cuda.empty_cache()
    seed = 0           
    random.seed(seed)
    torch.manual_seed(seed)
    torch.cuda.manual_seed(seed)
    numpy.random.seed(seed)
    torch.backends.cudnn.deterministic=True
    torch.backends.cudnn.benchmarks=False
    os.environ['PYTHONHASHSEED'] = str(seed)
    device = torch.device("cuda:0")
    def applyGaussSmooth(kernalSize,Variance,data):
        gMean = (kernalSize-1.)/2.     #Get float mean
        ##  watch -d -n 0.5 nvidia-smi

    from DLStudio import *

    dls = DLStudio(
                    dataroot = "C:/CodeRepos/BME695/HW5/DLStudio-1.1.0/Examples/data/",
                    image_size = [32,32],
                    path_saved_model = "./saved_model",
                    momentum = 0.9,
                    learning_rate = 1e-4,
                    epochs = 4,
                    batch_size = 4,
                    classes = ('rectangle','triangle','disk','oval','star'),
                    debug_train = 1,
                    debug_test = 1,
                    use_gpu = True,
                )


    detector = DLStudio.DetectAndLocalize( dl_studio = dls )
    dataserver_train = DLStudio.DetectAndLocalize.PurdueShapes5Dataset(
                                    train_or_test = 'train',
                                    dl_studio = dls,
                                      dataset_file = "PurdueShapes5-10000-train.gz", 
    #                                dataset_file = "PurdueShapes5-10000-train-noise-20.gz", 
    #                                   dataset_file = "PurdueShapes5-10000-train-noise-50.gz", 
    #                                   dataset_file = "PurdueShapes5-10000-train-noise-80.gz", 
                                                                        )
    dataserver_test = DLStudio.DetectAndLocalize.PurdueShapes5Dataset(
                                    train_or_test = 'test',
                                    dl_studio = dls,
                                       dataset_file = "PurdueShapes5-1000-test.gz"
    #                               dataset_file = "PurdueShapes5-1000-test-noise-20.gz"
    #                                   dataset_file = "PurdueShapes5-1000-test-noise-50.gz"
    #                                   dataset_file = "PurdueShapes5-1000-test-noise-80.gz"
                                                                    )
    detector.dataserver_train = dataserver_train
    detector.dataserver_test = dataserver_test
    detector.load_PurdueShapes5_dataset(dataserver_train, dataserver_test)

    model = EdgeNet(3,5,4,0)#detector.LOADnet2(skip_connections=True, depth=32)
    model = model.to(device)          #On Windows, DLStudio does not send model to device till second pass of forward. No idea why
    dls.show_network_summary(model)
    detector.run_code_for_training_with_CrossEntropy_and_MSE_Losses(model)
    #detector.run_code_for_training_with_CrossEntropy_and_BCE_Losses(model)

    #import pymsgbox
    #response = pymsgbox.confirm("Finished training.  Start testing on unseen data?")
    #if response == "OK": 
    detector.run_code_for_testing_detection_and_localization(model)

