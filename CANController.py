import lawicel_canusb
import time
import sys
if sys.platform == "win32":
    from time import clock as getts
else:
    from time import time as getts
import threading
import copy
from collections import deque

frames=[]
frameCounts={}
lastFramesByID={}

class WorkerThread(threading.Thread):
    def __init__(self, canusb, lock, callback):
        threading.Thread.__init__(self)
        self._canusb = canusb
        self._abort = 0
        self._tx_frames = deque()
        self._tx_scheduled_frames = []
        self._lock = lock
        self._callback = callback
        
    def run(self):
        global frames
        global frameCounts
        global lastFramesByID
        
        frames=[]
        frameCounts={}
        lastFrameByID={}
        
        startTime = getts()
        lastRefresh = startTime
        lastErrorCheck = startTime
        while not self._abort:
            # Check for bus errors once per second
            if (getts()-lastErrorCheck) > 1.0:
                lastErrorCheck = getts()
                status_response = self._canusb.get_status_flags()
                
                print status_response
                
                if len(status_response) > 2:      
                    # status is 'F' followed by  2 bytes of hexadecimal BCD that represent the 8 bit status
                    status = (int(chr(status_response[1]),16) << 4) + int(chr(status_response[2]),16)
                    
                    if status > 0:
                        status_message = ""
                        rxFifoFull = status & 0x01
                        if rxFifoFull > 0:
                            status_message += " (RX Fifo full) "
                        txFifoFull = status & 0x02
                        if txFifoFull > 0:
                            status_message += " (TX Fifo full) "
                        errorWarning = status & 0x04
                        if errorWarning > 0:
                            status_message += " (Error Warning) "
                        dataOverrun = status & 0x08
                        if dataOverrun > 0:
                            status_message += " (Data Overrun) "
                        errorPassive = status & 0x20
                        if errorPassive > 0:
                            status_message += " (Error Passive) "
                        arbitrationLost = status & 0x40
                        if arbitrationLost > 0:
                            status_message += " (Arbitration Lost) "
                        busError = status & 0x80
                        if busError > 0:
                            status_message += " (Bus Error) "
                        
                        print "Bus status changed: 0x%x %s" % (status, status_message)
                        
            
            # Check whether it is time to send scheduled frames
            # and insert scheduled frames in the tx queue
            if 0 == len(self._tx_frames):
                for f in self._tx_scheduled_frames:
                    self._tx_frames.appendleft(f) 
                    
            try:
                # is it time to send a scheduled frame 
                if len(self._tx_frames) > 0:
                    # send any available frame, this will also read incoming frames
                    f = self._tx_frames.pop()
                    r = self._canusb.transmit_frame(f)
                else:
                    # poll if there are no frames to send
                    r = self._canusb.poll()
            except lawicel_canusb.CANUSBError, e:
                # re-raise error if it's not timeout
                if str(e).find("timeout") < 0:
                    raise
                else:
                    continue
            
            rxfifoLen = self._canusb.get_rxfifo_len()
            self._lock.acquire()
            for i in range(0, rxfifoLen):
                f = self._canusb.get_rx_frame()
                frames.append(f)
                if f.get_msg_id() not in frameCounts:
                    frameCounts[f.get_msg_id()]=1
                else:
                    frameCounts[f.get_msg_id()]=frameCounts[f.get_msg_id()]+1
                    
                lastFramesByID[f.get_msg_id()]=f
            self._lock.release()
            
                            
            # notify that new frames have been received if a callback
            # was provided
            # Only notify 5 times/s or every 100 frames to avoid 
            # over-loading the UI thread with events 
            if (self._callback != None) and ((len(frames) % 100 == 0) or ((getts()-lastRefresh) > 0.2)): 
                self._callback(len(frames))
                lastRefresh = getts()
                                                    
    def abort(self):
        self._abort = 1
        
    def send(self, f):
        self._tx_frames.appendleft(f)
        
    def schedule(self, f, intervalms):
        self._tx_scheduled_frames.append(f)
        
        
class CANUSBController(object):
    def __init__(self, serialPort, speed):
        self._serialPort = serialPort
        self._speed = speed
        self._worker = None
        self._canusb = None
        self._lock = threading.Lock()
        
    def Start(self, callback):
        self._canusb = lawicel_canusb.opencan(self._serialPort, self._speed)
        
        if not self._worker:          
            self._worker = WorkerThread(self._canusb, self._lock, callback)
            self._worker.start()
    
    def Stop(self):
        try:
            if self._worker:
                self._worker.abort()
                self._worker.join()
                self._worker = None
        finally:
            if self._canusb:
                self._canusb.close_channel()
                del self._canusb
                self._canusb = None            
            
    def GetFrame(self, index):
        global frames
        f = None
        self._lock.acquire()
        if index < len(frames):
            f = frames[index]
        self._lock.release()
        return f
    
    def GetTotalFrameCount(self):
        global frames
        return len(frames)
    
    def GetFrameCounts(self):
        global frameCounts
        self._lock.acquire()
        counts = copy.deepcopy(frameCounts)
        self._lock.release()
        return counts
    
    def GetLastFramesByID(self):
        global lastFramesByID
        self._lock.acquire()
        lastFrames = copy.deepcopy(lastFramesByID)
        self._lock.release()
        return lastFrames
    
    def ClearFrames(self):
        global frames
        global frameCounts
        self._lock.acquire()
        frames = []
        frameCounts = {}
        self._lock.release()
        
    def ScheduleFrames(self, frames):
        if self._worker:
            for f in frames:
                self._worker.schedule(f, 0)
        
    def SendFrames(self, delays, frames):
        if self._worker:
            for f in frames:
                self._worker.send(f)
    
if __name__ == "__main__":
    def print_callback(numFrames):
        print "received %d frames so far" % numFrames
        
    c = CANUSBController("COM3", 250000)
    c.Start(print_callback)
    time.sleep(10)
    c.Stop()
        
    