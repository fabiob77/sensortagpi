###
# Author:
#  Aaron D. Salinas (aaron_salinas@baylor.edu)
# Description:
#  This python application is intended to work with the TI
#  SensorTag (www.ti.com/sensortag) to take periodic sensor
#  readings and send notifications to console output.
#
#  Thingspeak and email notifications may be enabled 
#
# Date:
#  9 Dec. 2016
#

import pexpect
import argparse
import sys
import time
import json
import select
import threading
from thingspeak import *
from sensor_calcs import *
from mail import *

tag = None
bluetooth_adr = None

SLEEPTIME  = 30	# Readings taken every 30 seconds by default
TIMEOUT    = 30   # TIMEOUT to connect to device 
API_KEY    = None # Thingspeak API Key
EMAIL      = None # Email of notification's receiver
EMAIL_SLEEPTIME = 60 # Period for email notification updates, 60s by default


data = {} # Data (Sensor Readings)

# This function periodically sends an email notification to 
# an destination address untill the application is terminated
#
def emailNotification():
	print "Starting Email Notifications..."
	time.sleep(1)
	while True:	# Send email updates until application ends
		send_email(EMAIL, "Sensor Readings", tag.resultStr())	
		time.sleep(EMAIL_SLEEPTIME) #Send an email at the end of each sleeptime interval

class SensorTag:
	# Sensor Handles (From GATT Table)
	# (http://www.ti.com/ww/en/wireless_connectivity/sensortag2015/tearDown.html)	
	hnd = {'tmp': 0x21,'acc': 0x39,'hum': 0x29, 'mag': 0x39, 'gyro': 0x39, 'light': 0x41}
	

	global API_KEY
	global EMAIL

	def __init__( self, bluetooth_adr ):
		# Start gatttool
		self.con = pexpect.spawn('gatttool -b ' + bluetooth_adr + ' --interactive')
		self.con.expect('\[LE\]>', TIMEOUT) # timeout if no connection is made
		print "Preparing to connect. You might need to press the side button..."
		self.con.sendline('connect')
		# test for success of connect
		self.con.expect('Connection successful.*\[LE\]>', TIMEOUT)	

		# Enable the Sensors (Passing in decimal values)
		self.char_write_cmd(0x24, 01)  # Tmp

		# Motion Sensor Configuration
		# Refer to TI SensorTag website for motion sensors configuration options
		self.char_write_cmd(0x3c, 65535)
		self.char_write_cmd(0x2C ,01)  # Humidity
		self.char_write_cmd(0x44, 01)  # Light Sensativity

		# Call Initial Sensor Reading Calls
		# Initial Reading calls returns 0 (e.g. '00 00 00 00')
		self.char_read_hnd(self.hnd['tmp']) 	# TMP		
		self.char_read_hnd(self.hnd['acc'])		# Accerometer
		self.char_read_hnd(self.hnd['hum'])		# Humidity
		self.char_read_hnd(self.hnd['gyro'])	# Gyroscope
		self.char_read_hnd(self.hnd['light'])	# Light Sensativity
		
		if(EMAIL): #Start email notification
			email_thread = threading.Thread(name="email_notification", target=emailNotification)
			email_thread.daemon = True
			email_thread.start()

		return

	# This function sends a char write command to the Gatttool
	# connected to the SensorTag
	#
	def char_write_cmd( self, handle, value ):
		cmd = 'char-write-cmd 0x%02x %02d' % (handle, value)
		self.con.sendline(cmd)
		return

	# This function sends a char read handle command to the Gatttool
	# connected to the SensorTag
	#	
	# Args:
	#  handle - Handle of sensor to be read 
	# Return:
	#  Array of handle values (e.g. [10,a2,3b,FF])
	def char_read_hnd( self, handle ):
		cmd = 'char-read-hnd 0x%02x' % handle
		self.con.sendline(cmd)
		self.con.expect('descriptor: .*? \r')
		after = self.con.after
		rval = after.split()[1:]
		return [long(float.fromhex(n)) for n in rval]

	# This function continuously takes readings from the sensor tag and 
	# stores and displays readings for TMP006, Accelerometer (X-axis),
	# Humidity, Gyroscope (X-axis), and Light Sensativity
	#
	# Readings are taken every 30 seconds
	#
	# If the Thingspeak and/or Email notification options are enabled, then 
	# updates will be sent every 30s and 60s, respectively
	#
	def run(self):
		cnt = 0
		while True:
			print "\nReading..."
			# Read Tmp
			tmp_raw = self.char_read_hnd(self.hnd['tmp'])
			data['tmp'] = calcTmpTarget(tmp_raw)

			# Read Accelerometer
			acc_raw = self.char_read_hnd(self.hnd['acc'])	
			(acc, mag) = calcAccel(acc_raw)
			data['acc'] = acc[0] # Storing X value only

			# Read Humidity
			hum_raw = self.char_read_hnd(self.hnd['hum'])
			(t, rh) = calcHum(hum_raw)
			data['hum'] = rh

			# Read Gyroscope
			gyro_raw = self.char_read_hnd(self.hnd['gyro'])
			gyro = calcGyro(gyro_raw)			
			data['gyro'] = gyro[0] # Storing X value only						

			# Read Light Sensativity
			light_raw = self.char_read_hnd(self.hnd['light'])
			light = calcOpt(light_raw)
			data['light'] = light			
			cnt += 1
			print self.resultStr() # Display readings to output
					
			if(API_KEY):					# Thingspeak Notification
				thingspeak_update(API_KEY, data)

			time.sleep(SLEEPTIME)	

	# Readings taken from the SensorTag is formatted and put into a 
	# String
	#
	# Returns:
	#  s - Formatted reading data
	def resultStr(self):
		s =  'IR Temperature\t\t: %.2f F' % data['tmp']
		s += '\nAccelerometer (x-axis)\t: %.2f G' % data['acc']
		s += '\nHumidity\t\t: %.4f%%rH' % data['hum']
		s += '\nGyroscope (x-axis)\t: %.2f Deg.' % data['gyro']
		s += '\nLight\t\t\t: %.2f Lux' % data['light']
		return s

# This function prints the configurations for the 
# application
def printInfo():
	print "Starting Application..."
	# Sensortag Information
	print "  Sensortag Address: %s" % bluetooth_adr
	print "  Sampling Interval: %.0fs" % SLEEPTIME
	print "  Timeout: %.0fs" % TIMEOUT
	# Email
	if(API_KEY):
		print "  Thingspeak Noitifications Enabled"
		print "    API Key: %s" % API_KEY
	if(EMAIL):
		print "  Email Notifications Enabled"
		print "    Email: %s" % EMAIL
		print "    Email Interval: %.0fs" % EMAIL_SLEEPTIME
	print

def main():
	global TIMEOUT
	global SLEEPTIME
	global API_KEY
	global EMAIL
	global EMAIL_SLEEPTIME
	global tag
	global bluetooth_adr


	# Create Application Arguments/Flags
	parser = argparse.ArgumentParser(description='TI SensorTag Reading Notification Application.')	
	parser.add_argument('addr', help='SensorTag Bluetooth Address')
	parser.add_argument('--timeout',dest='timeout',type=float, metavar="TIMEOUT",help='Timeout period to connect to device. Default timeout is 30s.')
	parser.add_argument('-p','--period',dest='sleeptime', type=float, metavar='PERIOD',help='Time interval between sensor reading samples. Default is 30s')
	parser.add_argument('-k','--thingspeak-key' ,dest='key', metavar='KEY', help='Thingspeak API Key')
	parser.add_argument('-m',  '--mail', dest='mail', metavar='EMAIL', help='Email address destination')	
	parser.add_argument('--mail-period',dest='mail_sleeptime',type=float,metavar='PERIOD',help='Interval for email notification updates. Default is 60s')
	
	args = parser.parse_args() # Store Args
	
	bluetooth_adr = args.addr #Store the sensortag's address	
	if(args.sleeptime):
		SLEEPTIME = args.sleeptime
	if(args.timeout):
		TIMEOUT = args.timeout	
	if(args.key): 
		API_KEY = args.key	# Store Thingspeak API Key
	if(args.mail): 
		EMAIL = args.mail		# Store Destination Email Address
		if(args.mail_sleeptime):
			EMAIL_SLEEPTIME = args.mail_sleeptime

	printInfo() # Print application configurations for user
	
	try:
		tag = SensorTag(bluetooth_adr)
		tag.run() # Start SensorTag Readings
	except pexpect.TIMEOUT: # TIMEOUT error, no devices found
		print "No Devices Found! Shutting down application."				
	except (KeyboardInterrupt, SystemExit):
		sys.exit() # Stop Application

if __name__ == "__main__":
	main()