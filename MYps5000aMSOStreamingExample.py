#
# Copyright (C) 2018-2020 Pico Technology Ltd. See LICENSE file for terms.
#
# PS3000 Series (A API) STREAMING MODE EXAMPLE
# This example demonstrates how to call the ps3000a driver API functions in order to open a device, setup 2 channels and collects streamed data (1 buffer).
# This data is then plotted as mV against time in ns.

import ctypes
import numpy as np
import os
import matplotlib.pyplot as plt
import time
import sys

sys.path.append("C:\\Users\\AndersEriksson\\PythonTool\\picosdk-python-wrappers")

from picosdk.ps5000a import ps5000a as ps, PS5000A_CONDITION, PS5000A_DIGITAL_CHANNEL_DIRECTIONS
from picosdk.functions import adc2mV, assert_pico_ok, mV2adc

# Create chandle and status ready for use
chandle = ctypes.c_int16()
status = {}

# Open PicoScope 5000 Series device
# Resolution set to 12 Bit
resolution =ps.PS5000A_DEVICE_RESOLUTION["PS5000A_DR_12BIT"]
# Returns handle to chandle for use in future API functions
status["openunit"] = ps.ps5000aOpenUnit(ctypes.byref(chandle), None, resolution)

try:
    assert_pico_ok(status["openunit"])
except: # PicoNotOkError:

    powerStatus = status["openunit"]

    if powerStatus == 286:
        status["changePowerSource"] = ps.ps5000aChangePowerSource(chandle, powerStatus)
    elif powerStatus == 282:
        status["changePowerSource"] = ps.ps5000aChangePowerSource(chandle, powerStatus)
    else:
        raise

    assert_pico_ok(status["changePowerSource"])


enabled = 1
disabled = 0
analogue_offset = 0.0

# Set up channel A
# handle = chandle
# channel = PS5000A_CHANNEL_A = 0
# enabled = 1
# coupling type = PS5000A_DC = 1
# range = PS5000A_2V = 7
# analogue offset = 0 V
channel_range = ps.PS5000A_RANGE['PS5000A_2V']
status["setChA"] = ps.ps5000aSetChannel(chandle,
                                        ps.PS5000A_CHANNEL['PS5000A_CHANNEL_A'],
                                        enabled,
                                        ps.PS5000A_COUPLING['PS5000A_DC'],
                                        channel_range,
                                        analogue_offset)
assert_pico_ok(status["setChA"])

# Set up channel B
# handle = chandle
# channel = PS5000A_CHANNEL_B = 1
# enabled = 1
# coupling type = PS5000A_DC = 1
# range = PS5000A_2V = 7
# analogue offset = 0 V
status["setChB"] = ps.ps5000aSetChannel(chandle,
                                        ps.PS5000A_CHANNEL['PS5000A_CHANNEL_B'],
                                        enabled,
                                        ps.PS5000A_COUPLING['PS5000A_DC'],
                                        channel_range,
                                        analogue_offset)
assert_pico_ok(status["setChB"])


# Find maximum ADC count value
# handle = chandle
# pointer to value = ctypes.byref(maxADC)
maxADC = ctypes.c_int16()
status["maximumValue"] = ps.ps5000aMaximumValue(chandle, ctypes.byref(maxADC))
assert_pico_ok(status["maximumValue"])

# Set up digital port
# handle = chandle
# channel = PS3000A_DIGITAL_PORT0 = 0x80
# enabled = 1
# logicLevel = 10000 => the voltage level for transition from 0 to 1 is at 5V*10000/32767 = approx 1.5V
digital_port0 = ps.PS5000A_CHANNEL["PS5000A_DIGITAL_PORT0"]
status["SetDigitalPort"] = ps.ps5000aSetDigitalPort( chandle, digital_port0, 1, 10000)
assert_pico_ok(status["SetDigitalPort"])

# source = ps.PS5000A_CHANNEL["PS5000A_CHANNEL_B"]
# threshold = int(mV2adc(1000,channel_range, maxADC))
# status["trigger"] = ps.ps5000aSetSimpleTrigger(chandle, 1, source, threshold, 3, 0, 0)
# assert_pico_ok(status["trigger"])

# Set up trigger on digital channel
# Device will trigger when there is a transition from high to low on digital channel 5

# Set trigger conditions
# handle = chandle
# Trigger conditions:
# channelA            = PS3000A_CONDITION_DONT_CARE = 0
# channelB            = PS3000A_CONDITION_DONT_CARE = 0
# channelC            = PS3000A_CONDITION_DONT_CARE = 0
# channelD            = PS3000A_CONDITION_DONT_CARE = 0
# external            = PS3000A_CONDITION_DONT_CARE = 0
# aux                 = PS3000A_CONDITION_DONT_CARE = 0
# pulseWidthQualifier = PS3000A_CONDITION_DONT_CARE = 0
# digital             = PS3000A_CONDITION_TRUE = 1
# nConditions = 1

# set the digital trigger for a high bit on digital channel 0
conditions = ps.PS5000A_CONDITION(ps.PS5000A_CHANNEL["PS5000A_DIGITAL_PORT0"], ps.PS5000A_TRIGGER_STATE["PS5000A_CONDITION_TRUE"])
nConditions = 1
clear = 1
add = 2
info = clear + add
status["setTriggerChannelConditionsV2"] = ps.ps5000aSetTriggerChannelConditionsV2(chandle,
                                                                                  ctypes.byref(conditions),
                                                                                  nConditions,
                                                                                  info)
assert_pico_ok(status["setTriggerChannelConditionsV2"])

# Set digital trigger directions

# handle = chandle
# Digital directions
# channel = PS3000A_DIGITAL_CHANNEL_0 = 0
# direction = PS3000A_DIGITAL_DIRECTION_RISING = 3
# nDirections = 1

directions = ps.PS5000A_DIGITAL_CHANNEL_DIRECTIONS(ps.PS5000A_DIGITAL_CHANNEL["PS5000A_DIGITAL_CHANNEL_0"], ps.PS5000A_DIGITAL_DIRECTION["PS5000A_DIGITAL_DIRECTION_HIGH"])
nDirections = 1
status["setTriggerDigitalPortProperties"] = ps.ps5000aSetTriggerDigitalPortProperties(chandle,
                                                                                      ctypes.byref(directions),
                                                                                      nDirections)
assert_pico_ok(status["setTriggerDigitalPortProperties"])

# # set autotrigger timeout value
# status["autoTriggerus"] = ps.ps5000aSetAutoTriggerMicroSeconds(chandle, 10000)
# assert_pico_ok(status["autoTriggerus"])

print ("Starting data collection...")

#define sample data
sample_period_us = 1
total_time_sec = 0.01
trig_pos = 5 # 40%

# Size of capture
sizeOfOneBuffer = int(5000 / sample_period_us) # => 5ms
totalSamples = int(1_000_000 * total_time_sec / sample_period_us)

# Create buffers ready for assigning pointers for data collection
bufferAMax = np.zeros(shape=sizeOfOneBuffer, dtype=np.int16)
bufferBMax = np.zeros(shape=sizeOfOneBuffer, dtype=np.int16)

memory_segment = 0

# Set data buffer location for data collection from channel A
# handle = chandle
# source = PS3000A_CHANNEL_A = 0
# pointer to buffer max = ctypes.byref(bufferAMax)
# pointer to buffer min = ctypes.byref(bufferAMin)
# buffer length = maxSamples
# segment index = 0
# ratio mode = PS3000A_RATIO_MODE_NONE = 0
status["setDataBuffersA"] = ps.ps5000aSetDataBuffers(chandle,
                                                     ps.PS5000A_CHANNEL['PS5000A_CHANNEL_A'],
                                                     bufferAMax.ctypes.data_as(ctypes.POINTER(ctypes.c_int16)),
                                                     None,
                                                     sizeOfOneBuffer,
                                                     memory_segment,
                                                     ps.PS5000A_RATIO_MODE['PS5000A_RATIO_MODE_NONE'])
assert_pico_ok(status["setDataBuffersA"])

# Set data buffer location for data collection from channel B
# handle = chandle
# source = PS3000A_CHANNEL_B = 1
# pointer to buffer max = ctypes.byref(bufferBMax)
# pointer to buffer min = ctypes.byref(bufferBMin)
# buffer length = maxSamples
# segment index = 0
# ratio mode = PS3000A_RATIO_MODE_NONE = 0
status["setDataBuffersB"] = ps.ps5000aSetDataBuffers(chandle,
                                                     ps.PS5000A_CHANNEL['PS5000A_CHANNEL_B'],
                                                     bufferBMax.ctypes.data_as(ctypes.POINTER(ctypes.c_int16)),
                                                     None,
                                                     sizeOfOneBuffer,
                                                     memory_segment,
                                                     ps.PS5000A_RATIO_MODE['PS5000A_RATIO_MODE_NONE'])
assert_pico_ok(status["setDataBuffersB"])

bufferDPort0Max = np.zeros(shape=sizeOfOneBuffer, dtype=np.int16)
# Set the data buffer location for data collection from PS3000A_DIGITAL_PORT0
# handle = chandle
# source = PS3000A_DIGITAL_PORT0 = 0x80
# Buffer max = ctypes.byref(bufferDPort0Raw)
# Buffer length = totalSamples
# Segment index = 0
# Ratio mode = PS3000A_RATIO_MODE_NONE = 0
status["SetDataBuffer"] = ps.ps5000aSetDataBuffers(chandle,
												  digital_port0,
                                                  bufferDPort0Max.ctypes.data_as(ctypes.POINTER(ctypes.c_int16)),
  												  None,
												  sizeOfOneBuffer,
												  memory_segment,
												  ps.PS5000A_RATIO_MODE['PS5000A_RATIO_MODE_NONE'])
assert_pico_ok(status["SetDataBuffer"])

# Begin streaming mode:
sampleInterval = ctypes.c_int32(sample_period_us)
sampleUnits = ps.PS5000A_TIME_UNITS['PS5000A_US']

maxPreTriggerSamples = int(totalSamples * trig_pos / 100)
autoStopOn = 1
# No downsampling:
downsampleRatio = 1
status["runStreaming"] = ps.ps5000aRunStreaming(chandle,
                                                ctypes.byref(sampleInterval),
                                                sampleUnits,
                                                maxPreTriggerSamples,
                                                totalSamples - maxPreTriggerSamples,
                                                autoStopOn,
                                                downsampleRatio,
                                                ps.PS5000A_RATIO_MODE['PS5000A_RATIO_MODE_NONE'],
                                                sizeOfOneBuffer)
assert_pico_ok(status["runStreaming"])

print("Capturing at sample interval %s us" % sample_period_us)

# We need a big buffer, not registered with the driver, to keep our complete capture in.
from collections import deque
bufferCompleteA = deque(np.zeros(shape=totalSamples, dtype=np.int16), maxlen=totalSamples)
bufferCompleteB = deque(np.zeros(shape=totalSamples, dtype=np.int16), maxlen=totalSamples)
bufferCompleteDPort0 = deque(np.zeros(shape=totalSamples, dtype=np.int16), maxlen=totalSamples)
nextSample = 0
autoStopOuter = False
wasCalledBack = False

#AE own
post_trig = False
trigged_at = 0
stream_call_cnt_since_last_get_streaming = 0
max_stream_call_cnt_since_last_get_streaming = 0
max_samples_recieved_cnt = 0
last_get_streaming_lastest_values_cnt = 0
lowest_no_samples_recieved = sizeOfOneBuffer
no_of_samples_distribution = np.zeros(51)
get_streaming_cnt_since_last_stream_call = 0
max_get_streaming_cnt_since_last_stream_call = 0
overflow_state = []

def streaming_callback(handle, noOfSamples, startIndex, overflow, triggerAt, triggered, autoStop, param):
    global nextSample, autoStopOuter, wasCalledBack, post_trig, trigged_at, overflow_state, max_samples_recieved_cnt
    global lowest_no_samples_recieved, no_of_samples_distribution, last_get_streaming_lastest_values_cnt
    global stream_call_cnt_since_last_get_streaming, max_stream_call_cnt_since_last_get_streaming
    global get_streaming_cnt_since_last_stream_call
    
    if overflow:
        overflow_state = [overflow, nextSample]
        
    get_streaming_cnt_since_last_stream_call = 0;
    stream_call_cnt_since_last_get_streaming += 1
    
    if max_stream_call_cnt_since_last_get_streaming < stream_call_cnt_since_last_get_streaming:
        max_stream_call_cnt_since_last_get_streaming = stream_call_cnt_since_last_get_streaming
    
    no_of_samples_distribution[noOfSamples // 100] += 1
    if sizeOfOneBuffer == noOfSamples:
        max_samples_recieved_cnt += 1
    elif lowest_no_samples_recieved > noOfSamples:
        lowest_no_samples_recieved = noOfSamples
    wasCalledBack = True
    if triggered:
        post_trig = True
        trigged_at = triggerAt
        nextSample -= triggerAt
         
    sourceEnd = startIndex + noOfSamples
    bufferCompleteA.extend(bufferAMax[startIndex:sourceEnd])
    bufferCompleteB.extend(bufferBMax[startIndex:sourceEnd])
    bufferCompleteDPort0.extend(bufferDPort0Max[startIndex:sourceEnd])
    if autoStop:
        autoStopOuter = True

    if post_trig or nextSample < maxPreTriggerSamples:
        nextSample += noOfSamples

            
# Convert the python function into a C function pointer.
cFuncPtr = ps.StreamingReadyType(streaming_callback)

# Fetch data from the driver in a loop, copying it out of the registered buffers and into our complete one.
try:
    while nextSample < totalSamples and not autoStopOuter:
        print(f'\r[{nextSample * 100 / totalSamples:.1f}%] received', end='')
        wasCalledBack = False
        stream_call_cnt_since_last_get_streaming = 0;
        status["getStreamingLastestValues"] = ps.ps5000aGetStreamingLatestValues(chandle, cFuncPtr, None)
        get_streaming_cnt_since_last_stream_call += 1
        if max_get_streaming_cnt_since_last_stream_call < get_streaming_cnt_since_last_stream_call:
            max_get_streaming_cnt_since_last_stream_call = get_streaming_cnt_since_last_stream_call
        if not wasCalledBack:
            # If we weren't called back by the driver, this means no data is ready. Sleep for a short while before trying
            # again.
            time.sleep(0.002)
except KeyboardInterrupt:
    os.abort()
            
print(f'\r[{nextSample * 100 / totalSamples:.1f}%] received')

print("Done grabbing values.")

# Find maximum ADC count value
# handle = chandle
# pointer to value = ctypes.byref(maxADC)
maxADC = ctypes.c_int16()
status["maximumValue"] = ps.ps5000aMaximumValue(chandle, ctypes.byref(maxADC))
assert_pico_ok(status["maximumValue"])

# Convert ADC counts data to mV
channelInputRanges = [10, 20, 50, 100, 200, 500, 1000, 2000, 5000, 10000, 20000, 50000, 100000, 200000]
vRange = channelInputRanges[channel_range]
adc2mVChAMax = np.asarray(bufferCompleteA).astype(float) * vRange / maxADC.value
adc2mVChBMax = np.asarray(bufferCompleteB).astype(float) * vRange / maxADC.value

print(f'trigged_at = {trigged_at}')
print(f'max_samples_recieved_cnt = {max_samples_recieved_cnt}')
print(f'lowest_no_samples_recieved = {lowest_no_samples_recieved}')
print(f'max_stream_call_cnt_since_last_get_streaming = {max_stream_call_cnt_since_last_get_streaming}')
print(f'max_get_streaming_cnt_since_last_stream_call = {max_get_streaming_cnt_since_last_stream_call}')
print(f'overflow_state = {overflow_state}')
print(f'autoStopOuter = {autoStopOuter}')
print(f'no_of_samples_distribution = {no_of_samples_distribution}')


def splitMSO_np_version(buffer):
	np_buffer = np.ctypeslib.as_array(buffer)
	d = lambda n: (np_buffer & (1 << n)) >> n
	return [d(n) for n in range(8)]
		
digital_data = splitMSO_np_version(np.asarray(bufferCompleteDPort0))

skip_every = 1 
adc2mVChAMax = adc2mVChAMax[::skip_every]
adc2mVChBMax = adc2mVChBMax[::skip_every]

d5 = digital_data[0][::skip_every]

# Create time data
#time = np.linspace(0, (totalSamples) * actualSampleIntervalNs, totalSamples)
total_time = int(totalSamples / skip_every)
time = np.linspace(0, total_time - 1, total_time)

# Plot data from channel A and B
plt.plot(time, adc2mVChAMax,'-*')
plt.plot(time, adc2mVChBMax)
plt.plot(time,d5*100+100)
plt.xlabel('Time (us)')
plt.ylabel('Voltage (mV)')
plt.grid()
plt.show()

# Stop the scope
# handle = chandle
status["stop"] = ps.ps5000aStop(chandle)
assert_pico_ok(status["stop"])

# Disconnect the scope
# handle = chandle
status["close"] = ps.ps5000aCloseUnit(chandle)
assert_pico_ok(status["close"])

# Display status returns
print(status)
