# grovepi_lcd_dht.py
#
# This is an project for using the Grove RGB_LED Display and the Grove DHT Sensor from the GrovePi starter kit
# 
# In this project, the Temperature and humidity from the DHT sensor is printed on the RGB_LCD Display
import decimal
from grovepi import *
from grove_rgb_lcd import *
import random
import time
import sys

# Using the Python Device SDK for IoT Hub:
#   https://github.com/Azure/azure-iot-sdk-python
# The sample connects to a device-specific MQTT endpoint on your IoT Hub.
import iothub_client
# pylint: disable=E0611
from iothub_client import IoTHubClient, IoTHubClientError, IoTHubTransportProvider, IoTHubClientResult
from iothub_client import IoTHubMessage, IoTHubMessageDispositionResult, IoTHubError, DeviceMethodReturnValue

# The device connection string to authenticate the device with your IoT hub.
# Using the Azure CLI:
# az iot hub device-identity show-connection-string --hub-name {YourIoTHubName} --device-id MyNodeDevice --output table
CONNECTION_STRING = "HostName=fbhub001.azure-devices.net;DeviceId=CC2541-fb-Room2;SharedAccessKey=q8wg+U5a+oZaPxEMmuOr7xa8zTgILqhXMa8yiqdCgBY="

# Using the MQTT protocol.
PROTOCOL = IoTHubTransportProvider.MQTT
MESSAGE_TIMEOUT = 10000

dht_sensor_port = 7     # Connect the DHt sensor to port 7
lastTemp = 0.1          # initialize a floating point temp variable
lastHum = 0.1           # initialize a floating Point humidity variable
tooLow = 62.0           # Lower limit in fahrenheit
justRight = 68.0        # Perfect Temp in fahrenheit
tooHigh = 74.0          # Temp Too high


# Function Definitions
def CtoF( tempc ):
   "This converts celcius to fahrenheit"
   tempf = round((tempc * 1.8) + 32, 2)
   return tempf

def FtoC( tempf ):
   "This converts fahrenheit to celcius"
   tempc = round((tempf - 32) / 1.8, 2)
   return tempc

def calcColorAdj(variance):     # Calc the adjustment value of the background color
    "Because there is 6 degrees mapping to 255 values, 42.5 is the factor for 12 degree spread"
    factor = 42.5
    adj = abs(int(factor * variance))
    if adj > 255:
        adj = 255
    return adj

def calcBG(ftemp):
    "This calculates the color value for the background"
    variance = ftemp - justRight;   # Calculate the variance
    adj = calcColorAdj(variance);   # Scale it to 8 bit int
    bgList = [0,0,0]               # initialize the color array
    if(variance < 0):
        bgR = 0;                    # too cold, no red
        bgB = adj;                  # green and blue slide equally with adj
        bgG = 255 - adj
        
    elif(variance == 0):             # perfect, all on green
        bgR = 0
        bgB = 0
        bgG = 255
        
    elif(variance > 0):             #too hot - no blue
        bgB = 0
        bgR = adj;                  # Red and Green slide equally with Adj
        bgG = 255 - adj
        
    bgList = [bgR,bgG,bgB]          #build list of color values to return
    return bgList

while True:

    try:
        temp = 0.01
        hum = 0.01
        [ temp,hum ] = dht(dht_sensor_port,0)       #Get the temperature and Humidity from the DHT sensor
                                                    #Change the second parameter to 0 when using DHT (instead of DHT Pro)
                                                    #You will get very large number values if you don't!
        if (CtoF(temp) != lastTemp) and (hum != lastHum) and not math.isnan(temp) and not math.isnan(hum):
                #print("lowC : ",FtoC(tooLow),"C\t\t","rightC  : ", FtoC(justRight),"C\t\t","highC : ",FtoC(tooHigh),"C") # comment these three lines
                #print("lowF : ",tooLow,"F\t\tjustRight : ",justRight,"F\t\ttoHigh : ",tooHigh,"F")                       # if no monitor display
                print("tempC : ", temp, "C\t\ttempF : ",CtoF(temp),"F\t\tHumidity =", hum,"%\r\n")
                
                lastHum = hum          # save temp & humidity values so that there is no update to the RGB LCD
                ftemp = CtoF(temp)     # unless the value changes
                ftemp = temp     # unless the value changes
                lastTemp = ftemp       # this reduces the flashing of the display
                # print "ftemp = ",ftemp,"  temp = ",temp   # this was just for test and debug
                
                bgList = calcBG(ftemp)           # Calculate background colors
                
                t = str(ftemp)   # "stringify" the display values
                h = str(hum)
                # print "(",bgList[0],",",bgList[1],",",bgList[2],")"   # this was to test and debug color value list
                setRGB(bgList[0],bgList[1],bgList[2])   # parse our list into the color settings
                setText("Temp:" + t + "C      " + "Humidity :" + h + "%") # update the RGB LCD display
                
                # Define the JSON message to send to IoT Hub.
                #TEMPERATURE = temp
                #HUMIDITY = hum
                #MSG_TXT = "{\"temperature\": 'temp' ,\"humidity\": 'hum'}"
                MSG_TXT = "{\"DeviceRef\": \"CC2541-fb-Room2\",\"Temp\": %.2f, \"Humidity\": %.2f}"
                def send_confirmation_callback(message, result, user_context):
                    print ( "IoT Hub responded to message with status: %s" % (result) )

                def iothub_client_init():
                # Create an IoT Hub client
                # client.set_option("auto_url_encode_decode", True)
                    client = IoTHubClient(CONNECTION_STRING, PROTOCOL)
                    return client

                def iothub_client_telemetry_sample_run():

                    client = iothub_client_init()
                    print ( "IoT Hub device sending periodic messages, press Ctrl-C to exit" )

                    while True:
                        # Build the message with real telemetry values.
                        temperature = temp
                        humidity = hum
                        msg_txt_formatted = MSG_TXT % (temperature, humidity)
                        message = IoTHubMessage(msg_txt_formatted)
                        # print("JSON payload = " + msg_txt_formatted)

                        # Add a custom application property to the message.
                        # An IoT hub can filter on these properties without access to the message body.
                        prop_map = message.properties()
                        if temperature > 30:
                          prop_map.add("temperatureAlert", "true")
                        else:
                          prop_map.add("temperatureAlert", "false")

                        # Send the message.
                        print( "Sending message: %s" % message.get_string() )
                        client.send_event_async(message, send_confirmation_callback, None)
                        time.sleep(1)
                    #except IoTHubError as iothub_error:
                    #    print ( "Unexpected error %s from IoTHub" % iothub_error )
                    #    return
                    #except KeyboardInterrupt:
                    #    print ( "IoTHubClient sample stopped" )

                #if __name__ == '__main__':
                #    print ( "IoT Hub Quickstart #1 - real device" )
                #    print ( "Press Ctrl-C to exit" )
                    
                
    except (IOError,TypeError) as e:
        print("Error" + str(e))
        iothub_client_telemetry_sample_run()