#=============================================================================
# Copyright 2017 FLIR Integrated Imaging Solutions, Inc. All Rights Reserved.
#
# This software is the confidential and proprietary information of FLIR
# Integrated Imaging Solutions, Inc. ("Confidential Information"). You
# shall not disclose such Confidential Information and shall use it only in
# accordance with the terms of the license agreement you entered into
# with FLIR Integrated Imaging Solutions, Inc. (FLIR).
#
# FLIR MAKES NO REPRESENTATIONS OR WARRANTIES ABOUT THE SUITABILITY OF THE
# SOFTWARE, EITHER EXPRESSED OR IMPLIED, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR
# PURPOSE, OR NON-INFRINGEMENT. FLIR SHALL NOT BE LIABLE FOR ANY DAMAGES
# SUFFERED BY LICENSEE AS A RESULT OF USING, MODIFYING OR DISTRIBUTING
# THIS SOFTWARE OR ITS DERIVATIVES.
#=============================================================================

#TODO: 1. automatically get ROI (done)
#      2. increase trial num
#      3. user UI: select folder; easy preview

import PyCapture2
from sys import exit
from time import sleep, time
import numpy as np

trial_time_out = 50  # If no frame arrives in trial_time_out, restart a new trial (overhead ~ 10 ms)

def printBuildInfo():
	libVer = PyCapture2.getLibraryVersion()
	print "PyCapture2 library version: ", libVer[0], libVer[1], libVer[2], libVer[3]
	print

def printCameraInfo(cam):
	camInfo = cam.getCameraInfo()
	print "\n*** CAMERA INFORMATION ***\n"
	print "Serial number - ", camInfo.serialNumber
	print "Camera model - ", camInfo.modelName
	print "Camera vendor - ", camInfo.vendorName
	print "Sensor - ", camInfo.sensorInfo
	print "Resolution - ", camInfo.sensorResolution
	print "Firmware version - ", camInfo.firmwareVersion
	print "Firmware build time - ", camInfo.firmwareBuildTime
	print
	
	#bufferInfo = PyCapture2.Config()
	#print "Number Buffer - ", bufferInfo.numBuffers
	#print "grabMode - ", bufferInfo.grabMode
	#print "grabMode - ", bufferInfo.isochBusSpeed
	bufferInfo = cam.getConfiguration().__dict__
	print "Number Buffer - ", bufferInfo['numBuffers ']
	print "grabMode - ", bufferInfo['grabMode ']
	print "isochBusSpeed - ", bufferInfo['isochBusSpeed ']


def pollForTriggerReady(cam):
	#softwareTrigger = 0x62C
	externalTrigger = 0x830
	fireVal = 0x83100000
	cam.writeRegister(externalTrigger, fireVal)
	while True:	
		#regVal = cam.readRegister(softwareTrigger)
		regVal = cam.readRegister(externalTrigger)
		print regVal
		if regVal==regVal:
			break

#
# Example Main
#

def main(camera_serial_number, fileName_prefix):
	# Print PyCapture2 Library Information
	printBuildInfo()

	# Ensure sufficient cameras are found
	bus = PyCapture2.BusManager()
	numCams = bus.getNumOfCameras()
	print "Number of cameras detected: ", numCams
	if not numCams:
		print "Insufficient number of cameras. Exiting..."
		exit()

	c = PyCapture2.Camera()
	# c.connect(bus.getCameraFromIndex(camera_index))  
	c.connect(bus.getCameraFromSerialNumber(camera_serial_number))   # !!!


	# Power on the Camera
	cameraPower = 0x610
	powerVal = 0x80000000

	c.writeRegister(cameraPower, powerVal)

	# Waiting for camera to power up
	retries = 10
	timeToSleep = 0.1	#seconds
	for i in range(retries):
		sleep(timeToSleep)
		try:
			regVal = c.readRegister(cameraPower)
		except PyCapture2.Fc2error:	# Camera might not respond to register reads during powerup.
			pass
		awake = True
		if regVal == powerVal:
			break
		awake = False
	if not awake:
		print "Could not wake Camera. Exiting..."
		exit()

	# Configure trigger mode
	triggerMode = c.getTriggerMode()
	triggerMode.onOff = True
	triggerMode.mode = 14
	triggerMode.parameter = 0
	triggerMode.polarity = 1
	triggerMode.source = 0		# Using external trigger  !!!

	c.setTriggerMode(triggerMode)

	# Set external trigger
	#externalTrigger = 0x830
	#fireVal = 0x83100000
	#c.writeRegister(externalTrigger, fireVal)

	c.setConfiguration(grabTimeout = 1000000)

	# Print camera details
	fmt7info, supported = c.getFormat7Info(1)

	# Check whether pixel format mono8 is supported
	if PyCapture2.PIXEL_FORMAT.RAW8 & fmt7info.pixelFormatBitField == 0:
		print "Pixel format is not supported\n"
		exit()

	# Configure camera format7 settings
	# Left, Top, Width, Height
	# fmt7imgSet = PyCapture2.Format7ImageSettings(1, 0, 0, fmt7info.maxWidth, fmt7info.maxHeight, PyCapture2.PIXEL_FORMAT.RAW8)
	# fmt7imgSet = PyCapture2.Format7ImageSettings(0, 368, 296, 496, 416, PyCapture2.PIXEL_FORMAT.RAW8) # Camera 1 side
	# fmt7imgSet = PyCapture2.Format7ImageSettings(1, 144, 162, 304, 350, PyCapture2.PIXEL_FORMAT.RAW8) # Camera 1

	# Automatically get settings from the GUI (Han 20210414)
	setting_in_gui = c.getFormat7Configuration()[0]
	fmt7imgSet = PyCapture2.Format7ImageSettings(setting_in_gui.mode,
												 setting_in_gui.offsetX,
												 setting_in_gui.offsetY,
												 setting_in_gui.width,
												 setting_in_gui.height,
												 setting_in_gui.pixelFormat)
												 

	fmt7pktInf, isValid = c.validateFormat7Settings(fmt7imgSet)
	if not isValid:
		print "Format7 settings are not valid!"
		exit()
	c.setFormat7ConfigurationPacket(fmt7pktInf.maxBytesPerPacket, fmt7imgSet)

	# Enable camera embedded timestamp
	c.setEmbeddedImageInfo(timestamp = True)

	# Configure camera buffer settings
	#bufferFrame = PyCapture2.Config()
	#bufferFrame.numBuffers = 64
	#bufferFrame.grabMode = 1
	#bufferFrame.highPerformanceRetrieveBuffer = True

	c.setConfiguration(numBuffers = 64)
	c.setConfiguration(grabMode = 1)
	c.setConfiguration(highPerformanceRetrieveBuffer = True)
	
	# import pdb; pdb.set_trace()

	# Print camera details
	printCameraInfo(c)
	print "\n---------------- \n"
	print "Camera: ", fileName_prefix	
	print "mode = ", setting_in_gui.mode
	print "width * height = ", setting_in_gui.width, "*", setting_in_gui.height


	# --------------------------------------------------
	# Start acquisition
	c.startCapture()

	# avi = PyCapture2.AVIRecorder()  # This doesn't work for v2.13
	avi = PyCapture2.FlyCapture2Video()

	#fRateProp = c.getProperty(PyCapture2.PROPERTY_TYPE.FRAME_RATE)
	#frameRate = fRateProp.absValue
	frameRate = 30
	trialIdx = 1

	fileName = fileName_prefix + "{}.avi".format(trialIdx)
	#image = c.retrieveBuffer()
	#avi.AVIOpen(fileName, frameRate)
	avi.MJPGOpen(fileName, frameRate, 95)
	
	# Grab images
	try:
		while True: # Loop per trial
			frame_count = 0
			intervals = []
			last_frame = 0
			print "Trial=", '{:<4d}'.format(trialIdx), "  ",

			while True:
				try:
					image = c.retrieveBuffer()
					avi.append(image)

					frame_count += 1
					this_frame = time()
					intervals.append(this_frame - last_frame)
					# print image.getDataSize(), (this_frame - last_frame)*1000
					last_frame = this_frame

					if frame_count>0:   # Once first frame received, set Timeout to 100ms
						c.setConfiguration(grabTimeout = trial_time_out)
					
				except PyCapture2.Fc2error as fc2Err:
					#print "Error retrieving buffer : ", fc2Err
					avi.close()	# Close file

					trialIdx += 1
					fileName = fileName_prefix + "{}.avi".format(trialIdx)
					#avi.AVIOpen(fileName, frameRate)
					avi.MJPGOpen(fileName, frameRate, 95)
					#avi.H264Open(fileName, frameRate, image.getCols(), image.getRows(), 100000)
					c.setConfiguration(grabTimeout = 1000000)

					intervals.append(time() - last_frame)  # Gap between receiving the last frame and starting new file (including 100ms Timeout)
					#continue
					break

			#print "max frame interval = ", intervals
			#print np.histogram(intervals)
			interval_count, interval_edges = np.histogram(intervals[1:-1], 7)
			interval_bins = (interval_edges[:-1] + interval_edges[1:])/2
			print '{:5d} @ {:.3f} Hz'.format(frame_count, 1/np.mean(intervals[1:-1])), 
			print ''.join([" | {:.2f}ms:{:<4d}".format(bb*1000, nn) for nn, bb in zip(interval_count, interval_bins) if nn>0]),
			print '>> gap={:.3f}ms'.format(intervals[-1]*1000)
			
	except KeyboardInterrupt:   # Ctrl-C
		pass

			
	c.setTriggerMode(onOff = False)
	print "Finished grabbing images!"

	c.stopCapture()
	c.disconnect()

	# raw_input("Done! Press Enter to exit...\n")
