'''
Created on Aug 28, 2009

@author: frederic
'''

import CANMessage
import lawicel_canusb
import time
import sys

if __name__ == "__main__":
    if sys.platform=='win32':
        DEVICE = "COM3"
    else:
        DEVICE = "/dev/ttyUSB0"
    
    try:
        canusb = lawicel_canusb.opencan(DEVICE, 500000)
        count = 0
         
        startTime = time.time()
    
        while (1):
            try:
                #sig = CANMessage.CANSignal("test", 0x300+(count%8), 0, 'f64', 'motorola', 56, 64, count/((count%8)+1))
                sig = CANMessage.CANSignal("test", 0x300, 0, 'i32', 'intel', 4, 32, count)
                canusb.transmit_frame(sig.to_canframe())
                count = count + 1
            except lawicel_canusb.CANUSBError, e:
                # re-raise error if it's not timeout
                if str(e).find("timeout") < 0:
                    print "CANUSB error: " + str(e)
                    break
                else:
                    continue
                
            if count >= 500:
                duration = time.time()-startTime
                rate = float(count) / duration
                print "sent %d frames in %f s (%f frames/s)" % (count, duration, rate)
                startTime = time.time()
                count = 0;
    finally:     
        canusb.close_channel()
    
            
        
        