"""
ps5000_function.py
Channel A: Reference (16 bit)
Digital port 0: Camera exposure (External trigger)
Digital port 1: Chopper
==================
A function for using picoscope 5000 series
Created on 2024-05-09 by Ayumu Ishijima
"""
#%%
import numpy as np
import matplotlib.pyplot as plt
import cv2
import ctypes
import serial
import time as tm
import os
import sys
# sys.path.append("C:\\Users\\mikami\\Documents\\GitHub\\picosdk-python-wrappers")
sys.path.append("C:\\Users\\ayumu\\Documents\\GitHub\\picosdk-python-wrappers")
from picosdk.ps5000a import ps5000a as ps, PS5000A_CONDITION, PS5000A_DIGITAL_CHANNEL_DIRECTIONS
from picosdk.functions import adc2mV, assert_pico_ok, mV2adc

#%%


def ps5000_initialize(sample_period_us, total_time_sec, trig_pos):
    global sampleInterval, sampleUnits, totalSamples, autoStopOn, downsampleRatio, channel_range
    global sizeOfOneBuffer, bufferCompleteA, bufferCompleteB, bufferCompleteDPort0, maxPreTriggerSamples, bufferAMax, bufferBMax, bufferDPort0Max
    
    chandle = ctypes.c_int16()
    status = {}
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
    channel_range = ps.PS5000A_RANGE['PS5000A_2V']
    status["setChA"] = ps.ps5000aSetChannel(chandle,
                                            ps.PS5000A_CHANNEL['PS5000A_CHANNEL_A'],
                                            enabled,
                                            ps.PS5000A_COUPLING['PS5000A_DC'],
                                            channel_range,
                                            analogue_offset)
    assert_pico_ok(status["setChA"])
    
    # Set up channel B
    status["setChB"] = ps.ps5000aSetChannel(chandle,
                                            ps.PS5000A_CHANNEL['PS5000A_CHANNEL_B'],
                                            enabled,
                                            ps.PS5000A_COUPLING['PS5000A_DC'],
                                            channel_range,
                                            analogue_offset)
    assert_pico_ok(status["setChB"])    

    # Set up digital port
    digital_port0 = ps.PS5000A_CHANNEL["PS5000A_DIGITAL_PORT0"]
    status["SetDigitalPort"] = ps.ps5000aSetDigitalPort( chandle, digital_port0, 1, 10000)
    assert_pico_ok(status["SetDigitalPort"])
    
    # digital_port1 = ps.PS5000A_CHANNEL["PS5000A_DIGITAL_PORT1"]
    # status["SetDigitalPort"] = ps.ps5000aSetDigitalPort( chandle, digital_port1, 1, 10000)
    # assert_pico_ok(status["SetDigitalPort"])
    
    # Set the digital trigger for a high bit on digital channel 0
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
    directions = ps.PS5000A_DIGITAL_CHANNEL_DIRECTIONS(ps.PS5000A_DIGITAL_CHANNEL["PS5000A_DIGITAL_CHANNEL_0"], ps.PS5000A_DIGITAL_DIRECTION["PS5000A_DIGITAL_DIRECTION_HIGH"])
    nDirections = 1
    status["setTriggerDigitalPortProperties"] = ps.ps5000aSetTriggerDigitalPortProperties(chandle,
                                                                                        ctypes.byref(directions),
                                                                                        nDirections)
    assert_pico_ok(status["setTriggerDigitalPortProperties"])    

    # Find maximum ADC count value
    maxADC = ctypes.c_int16()
    status["maximumValue"] = ps.ps5000aMaximumValue(chandle, ctypes.byref(maxADC))
    assert_pico_ok(status["maximumValue"])
    
    
    
    # Size of capture
    sizeOfOneBuffer = int(5000 / sample_period_us) # => 5ms
    totalSamples = int(1_000_000 * total_time_sec / sample_period_us)
    
    # Create buffers ready for assigning pointers for data collection
    bufferAMax = np.zeros(shape=sizeOfOneBuffer, dtype=np.int16)
    bufferBMax = np.zeros(shape=sizeOfOneBuffer, dtype=np.int16)
    bufferDPort0Max = np.zeros(shape=sizeOfOneBuffer, dtype=np.int16)
    # bufferDPort1Max = np.zeros(shape=sizeOfOneBuffer, dtype=np.int16)

    memory_segment = 0
    
    # Set data buffer location for data collection from channel A
    status["setDataBuffersA"] = ps.ps5000aSetDataBuffers(chandle,
                                                        ps.PS5000A_CHANNEL['PS5000A_CHANNEL_A'],
                                                        bufferAMax.ctypes.data_as(ctypes.POINTER(ctypes.c_int16)),
                                                        None,
                                                        sizeOfOneBuffer,
                                                        memory_segment,
                                                        ps.PS5000A_RATIO_MODE['PS5000A_RATIO_MODE_NONE'])
    assert_pico_ok(status["setDataBuffersA"])    
    
    # Set data buffer location for data collection from channel B
    status["setDataBuffersB"] = ps.ps5000aSetDataBuffers(chandle,
                                                        ps.PS5000A_CHANNEL['PS5000A_CHANNEL_B'],
                                                        bufferBMax.ctypes.data_as(ctypes.POINTER(ctypes.c_int16)),
                                                        None,
                                                        sizeOfOneBuffer,
                                                        memory_segment,
                                                        ps.PS5000A_RATIO_MODE['PS5000A_RATIO_MODE_NONE'])
    assert_pico_ok(status["setDataBuffersB"])    
    
    # Set the data buffer location for data collection from PS3000A_DIGITAL_PORT0
    status["SetDataBuffer"] = ps.ps5000aSetDataBuffers(chandle,
                                                    digital_port0,
                                                    bufferDPort0Max.ctypes.data_as(ctypes.POINTER(ctypes.c_int16)),
                                                    None,
                                                    sizeOfOneBuffer,
                                                    memory_segment,
                                                    ps.PS5000A_RATIO_MODE['PS5000A_RATIO_MODE_NONE'])
    assert_pico_ok(status["SetDataBuffer"])    

    # # Set the data buffer location for data collection from PS3000A_DIGITAL_PORT0
    # status["SetDataBuffer"] = ps.ps5000aSetDataBuffers(chandle,
    #                                                 digital_port1,
    #                                                 bufferDPort1Max.ctypes.data_as(ctypes.POINTER(ctypes.c_int16)),
    #                                                 None,
    #                                                 sizeOfOneBuffer,
    #                                                 memory_segment,
    #                                                 ps.PS5000A_RATIO_MODE['PS5000A_RATIO_MODE_NONE'])
    # assert_pico_ok(status["SetDataBuffer"])   
        
    sampleInterval = ctypes.c_int32(sample_period_us)
    sampleUnits = ps.PS5000A_TIME_UNITS['PS5000A_US']

    maxPreTriggerSamples = int(totalSamples * trig_pos / 100)
    autoStopOn = 1
    # No downsampling:
    downsampleRatio = 1
    
    return chandle,status


def streaming_callback(handle, noOfSamples, startIndex, overflow, triggerAt, triggered, autoStop, param):
    global nextSample, autoStopOuter, wasCalledBack, post_trig, trigged_at, overflow_state, max_samples_recieved_cnt
    global lowest_no_samples_recieved, no_of_samples_distribution, last_get_streaming_lastest_values_cnt
    global stream_call_cnt_since_last_get_streaming, max_stream_call_cnt_since_last_get_streaming
    global get_streaming_cnt_since_last_stream_call
        
    if overflow:
        overflow_state = [overflow, nextSample]
        
    get_streaming_cnt_since_last_stream_call = 0
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
    # bufferCompleteDPort1.extend(bufferDPort1Max[startIndex:sourceEnd])
    if autoStop:
        autoStopOuter = True

    if post_trig or nextSample < maxPreTriggerSamples:
        nextSample += noOfSamples



def ps5000_acquire(chandle,status,sample_period_us, total_time_sec, trig_pos):
    global nextSample,stream_call_cnt_since_last_get_streaming, post_trig, last_get_streaming_lastest_values_cnt
    global nextSample, autoStopOuter, wasCalledBack, post_trig, trigged_at, overflow_state, max_samples_recieved_cnt
    global lowest_no_samples_recieved, no_of_samples_distribution, last_get_streaming_lastest_values_cnt
    global stream_call_cnt_since_last_get_streaming, max_stream_call_cnt_since_last_get_streaming
    global get_streaming_cnt_since_last_stream_call
    global bufferCompleteA, bufferCompleteB, bufferCompleteDPort0, sizeOfOneBuffer, totalSamples, sampleInterval, sampleUnits, maxPreTriggerSamples, autoStopOn, downsampleRatio, channel_range
    
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
    # bufferCompleteDPort1 = deque(np.zeros(shape=totalSamples, dtype=np.int16), maxlen=totalSamples)
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
    
    # Convert the python function into a C function pointer.
    cFuncPtr = ps.StreamingReadyType(streaming_callback)
    
    # Fetch data from the driver in a loop, copying it out of the registered buffers and into our complete one.
    try:
        while nextSample < totalSamples and not autoStopOuter:
            print(f'\r[{nextSample * 100 / totalSamples:.1f}%] received', end='')
            wasCalledBack = False
            stream_call_cnt_since_last_get_streaming = 0
            status["getStreamingLastestValues"] = ps.ps5000aGetStreamingLatestValues(chandle, cFuncPtr, None)
            get_streaming_cnt_since_last_stream_call += 1
            if max_get_streaming_cnt_since_last_stream_call < get_streaming_cnt_since_last_stream_call:
                max_get_streaming_cnt_since_last_stream_call = get_streaming_cnt_since_last_stream_call
            if not wasCalledBack:
                # If we weren't called back by the driver, this means no data is ready. Sleep for a short while before trying
                # again.
                tm.sleep(0.002)
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

    d0 = digital_data[0][::skip_every]
    d1 = digital_data[1][::skip_every]
    
    # Create time data
    #time = np.linspace(0, (totalSamples) * actualSampleIntervalNs, totalSamples)
    total_time = int(totalSamples / skip_every)
    time = np.linspace(0, total_time - 1, total_time)

    return adc2mVChAMax,adc2mVChBMax,d0,d1,time


def ps5000_close(chandle, status):
    status["stop"] = ps.ps5000aStop(chandle)
    assert_pico_ok(status["stop"])
    status["close"] = ps.ps5000aCloseUnit(chandle)
    assert_pico_ok(status["close"])
    print(status)

def myplot():
    plt.rcParams['font.family'] ='Arial'#使用するフォント
    plt.rcParams['xtick.direction'] = 'out'#x軸の目盛線が内向き('in')か外向き('out')か双方向か('inout')
    plt.rcParams['ytick.direction'] = 'out'#y軸の目盛線が内向き('in')か外向き('out')か双方向か('inout')
    plt.rcParams['xtick.minor.width'] = 1.0#x軸主目盛り線の線幅
    plt.rcParams['ytick.minor.width'] = 1.0#x軸主目盛り線の線幅
    plt.rcParams['xtick.major.width'] = 1.0#x軸主目盛り線の線幅
    plt.rcParams['ytick.major.width'] = 1.0#y軸主目盛り線の線幅
    plt.rcParams['font.size'] = 12 #フォントの大きさ
    plt.rcParams['axes.linewidth'] = 1.0# 軸の線幅edge linewidth。囲みの太さ
    plt.rcParams['figure.figsize'] = [3.14,3.14]# 図のサイズはインチで指定され、変数は(幅, 高さ)です。3.14 インチは約8cm。
    plt.rcParams['figure.dpi'] = 300
# %%
