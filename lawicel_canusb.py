"""CAN-USB test program

This demo program runs on a Linux PC and needs Python (http://www.python.org)
and PySerial (http://pyserial.sourceforge.net/).

CAN-USB is a USB to CAN adapter by www.lawicel.com. It contains an
FT245 USB controller. This test drives the FT245 as a serial port
which is slower compared to the parallel API. The product is also
described at www.canusb.com.

Hubert Hoegl, 2007-08-18, <hh at hhoegl.org>
"""

import serial, array, time, sys, getopt, atexit
from collections import deque
import CANMessage

BAUD = 115200
SERIAL_TIMEOUT = 1  # 1 msec

CR = 13
BELL = 7

sw_help = None
sw_test = None


class CANUSBError:
    def __init__(self, msg):
        self.msg = msg
    def __str__(self):
        return "Error: " + self.msg


class CANUSBFrame(CANMessage.CANFrame):
    def __init__(self, msg_id=0, xtd=0, rtr=0, ndata=0, data=() ):
        CANMessage.CANFrame.__init__(self, msg_id, xtd, rtr, ndata, data)    
    
    def to_ascii(self):
        """Convert Frame object to ASCII representation
           Examples for ASCII rep:
               tiiildd...
               Tiiiiiiiildd...
        """
        s_list=[]
        if self.xtd:
            s_list.append('T')
            s_list.append("%08x" % self.msg_id)
        else:
            s_list.append('t')
            s_list.append("%03x" % self.msg_id)
        
        s_list.append(str(self.ndata))
        
        for i in range(0, self.ndata, 1):
            s_list.append("%02x" % self.data[i])
          
        return "".join(s_list)

    def from_ascii(self, s):
        """Convert from ASCII representation s to Frame object
           Examples for ASCII rep:
               tiiildd...
               Tiiiiiiiildd...
        """
        if s[0] == 't':
            # standard frame
            self.msg_id = int(s[1:4], 16)
            self.ndata = int(s[4])
            s = s[5:]
            d = []
            for i in range(0, len(s), 2):
                d.append(int(s[i:i+2],16))
            self.data = tuple(d)
            self.rtr = 0
            self.xtd = 0

        elif s[0] == 'T':
            # extended frame
            self.msg_id = int(s[1:9], 16)
            self.ndata = int(s[9])
            s = s[10:]
            d = []
            for i in range(0, len(s), 2):
                d.append(int(s[i:i+2],16))
            self.data = tuple(d)
            self.rtr = 0
            self.xtd = 1
        else:
            pass # should never happen


class CanUSB(object):
    def __init__(self, device, baud):
        self.ser = serial.Serial(device, baud, timeout=SERIAL_TIMEOUT)
        self.rxfifo = deque()

    def __del__(self):
        self.ser.close()

    def empty_queue(self):
        # Tipp mentioned in the canusb manual
        return self.__send_command('\x0d\x0d\x0d')        

    def get_rxfifo_len(self):
        return len(self.rxfifo)

    def get_rx_frame(self):
        """Get an ASCII frame from the rxfifo and convert it to a
        Frame object which is returned. Return None if rxfifo is empty.
        """
        if len(self.rxfifo) > 0:
            fstr = self.rxfifo.pop()
            f = CANUSBFrame()
            f.from_ascii(fstr)
            del fstr
            return f
        else:
            return None

    def poll(self):
        """Check for incoming data packets. Note that also all other
        commands which write to the CANUSB dongle check for incoming
        data.
        """
        cmd = None
        return self.__send_command(cmd)

    def set_bitrate(self, bitrate):
        if bitrate == 10000:
            cmd = "S0"
        elif bitrate == 20000:
            cmd = "S1"
        elif bitrate == 50000:
            cmd = "S2"
        elif bitrate == 100000:
            cmd = "S3"
        elif bitrate == 250000:
            cmd = "S5"
        elif bitrate == 500000:
            cmd = "S6"
        elif bitrate == 800000:
            cmd = "S7"
        elif bitrate == 1000000:
            cmd = "S8"
        else:
            raise CANUSBError("currently only have 50 kbit/s")
        return self.__send_command(cmd)

    def set_btr0btr1(self, btr0, btr1):
        # e.g. s031C
        return self.__send_command("s"+btr0+btr1)

    def open_channel(self):
        return self.__send_command("O")

    def close_channel(self):
        return self.__send_command("C")

    def transmit_std(self, packet):
        """11bit CAN frame 
        packet -- iiildd...

           i : identifier 0-7ff
           l : length 0-8
           d : data

           Returns z[CR] or BELL
        """
        return self.__send_command('t' + packet)

    def transmit_ext(self, packet):
        """29bit CAN frame
        packet -- iiiiiiiildd...

           i : identifier 0-1fffffff
           l : length 0-8
           d : data

           Returns Z[CR] or BELL
        """
        return self.__send_command('T' + packet)
    
    def transmit_frame(self, f):
        usbf = CANUSBFrame(msg_id=f.get_msg_id(), xtd=f.get_xtd(), rtr=f.get_rtr(), ndata=f.get_ndata(), data=f.get_data())
        return self.__send_command(usbf.to_ascii())

    def get_status_flags(self):
        """Get the SJA1000 status flags

        The return value is a string coded as "F<digit1><digit2>".
        The bits in the digits are

           Bit 0 : CAN receive FIFO queue full
           Bit 1 : CAN transmit FIFO queue full
           Bit 2 : Error warning (EI), see SJA1000 datasheet
           Bit 3 : Data Overrun (DOI), see SJA1000 datasheet
           Bit 4 : Not used.
           Bit 5 : Error Passive (EPI), see SJA1000 datasheet
           Bit 6 : Arbitration Lost (ALI), see SJA1000 datasheet *
           Bit 7 : Bus Error (BEI), see SJA1000 datasheet **
        """
        return self.__send_command("F")

    def set_acc_code(self, code):
        """ Set SJA1000 accceptance code registers AC0, AC1, AC2, AC3
        code -- Hex string with 8 chars
        """
        return self.__send_command("M"+code)

    def set_acc_mask(self, mask):    
        """ Set SJA1000 accceptance mask registers AM0, AM1, AM2, AM3
        code -- Hex string with 8 chars
        """
        return self.__send_command("m"+mask)

    def get_version(self):
        return self.__send_command("V")

    def get_serial_number(self):
        return self.__send_command("N")

    def timestamp(self, onoff):
        """Set timestamp for received frames on or off. The timestamp
        is appended to the received packet and counts from 0 to 0xea5f.
        The timestamp counter is incremented every msec and wraps around
        after 60.000 msec (= 1 minute). This command is only active if
        the CAN channel is closed.
        
        onoff - a character '1' (on) or '0' (off)
        """
        return self.__send_command("Z"+onoff)

    def __send_command(self, cmd):
        """Send a command to the CANUSB dongle. Returns the command
        response as a list of integer values or an empty list if no
        command response.
        cmd -- A command string without the trailing [CR]
        """
        R = []

        if cmd:
            self.ser.write(cmd+chr(CR))

        while 1:
            d = self.ser.read(size=1)
            if not d:
                # timeout
                raise CANUSBError('ser.read returned None (timeout)')
            if d in ('t', 'T'):
                fstr = self.__parse_incoming_frame(d)
                self.rxfifo.appendleft(fstr)
                return R
                #continue
            if ord(d) == CR:
                # normal end of command response
                break
            if ord(d) == BELL and len(R) == 0:
                # canusb returned an error
                raise CANUSBError('ser.read returned BELL char (ERROR)')
                pass
            else:
                R.append( ord(d) )
        return R

    def __parse_incoming_frame(self, firstchar):
        """An incoming CAN frame is immediately sent over RS232 to the PC
        with the same formatting as for transmit packages. Every char
        returned from RS232 must be checked to be 't' or 'T' (see
        __send_command() ) . If this is the case a CAN packet is returned.

        firstchar -- either 't' or 'T'
        """
        if firstchar == 't':
            # simple frame
            n_id = 3
            r_packet = 't'
        if firstchar == 'T':
            # extended frame
            n_id = 8
            r_packet = 'T'
        s = self.ser.read(size=n_id + 1)  # id + data length
        # To Do: raise error if read does not work
        r_packet = r_packet + s
        n_data = ord(s[n_id])-ord('0')
        s = self.ser.read(size=n_data*2) # each byte has two chars
        # To Do: raise error if read does not work
        r_packet = r_packet + s
        s = self.ser.read(size=1) # final CR of 't/T' packet
        # To Do: raise error if read does not work
        return r_packet


def opencan(device, bitrate):
    c = CanUSB(device, BAUD)
    
    # Close channel in case it was left open
    # Ignore BELL error that will occur if the channel is closed
    try:
        c.close_channel()
    except CANUSBError, e:
        if str(e).find("BELL") < 0:
            raise

    c.set_bitrate(bitrate)

    # print "set_btr0btr1"
    # c.set_btr0btr1("34", "ce")

    c.open_channel()

    r = c.get_version()
    print "Version: %s" % r

    print "Serial: %s" % ltos(c.get_serial_number())
    return c
    

def ltos(l):
    a = array.array('B')
    a.fromlist(l)
    return a.tostring()

def stol(s):
    a = array.array('B')
    a.fromstring(s)
    return a.tolist()


def options():
    global sw_help, sw_test
    try:
        opt = getopt.getopt(sys.argv[1:], "h", ["help", "test="])
    except getopt.error, why:
        print why
        sys.exit(0)
    if opt == ([], []):
        usage()
        sys.exit(0)
    for o in opt[0]:
        if o[0] in ['-h', '--help']:
            sw_help = 1
            usage()
            sys.exit(1)
        if o[0] in ['--test']:
            sw_test = int(o[1])
    return opt[1]


def usage():
    print """%s [options]
-h, --help     Print help
--test=n       Run test number n
""" % (sys.argv[0],)


def test1():
    """Send five CAN messages (wait 1sec between) and wait 10sec for
    incoming data. Finally the number of received frames is printed.
    CAN speed is always 50 kbit/s.
    """
    c = opencan(50000)
    n = 0
    while n < 5:
        print '------------'
        f = "001801020304050607%02d"%n
        r = c.transmit_std(f)
        print "transmit_std", f, ltos(r)

        r = c.get_status_flags()
        print "get_status_flags:", ltos(r)

        time.sleep(1)
        n = n + 1

    print "check for incoming data"
    n = 0
    while n < 10:
        print n
        try:
            r = c.poll()
        except Error, e:
            # print e
            pass
        time.sleep(1)
        n = n + 1

    n = c.get_rxfifo_len()
    print "get_rxfifo_len =", n

    f = c.get_rx_frame()
    print "get_rx_frame:", f

    print "close_channel"
    c.close_channel()


def test2():
    c = opencan(50000)
    n = 0
    nrxmax = 5
    while n < nrxmax:
        try:
            r = c.poll()
            l = c.get_rxfifo_len()
            if l > 0:
                f = c.get_rx_frame()
                print f
                f = "00281122334455667788"
                print "sending frame"
                r = c.transmit_std(f)
                n = n + 1
        except Error, e:
            #print e
            pass

    print "close_channel"
    c.close_channel()


def test3():
    c = opencan(50000)
    n = 0
    while n < 5:
        print '------------'
        f = "001801020304050607%02d"%n
        r = c.transmit_std(f)
        print "transmit_std", f, ltos(r)

        r = c.get_status_flags()
        print "get_status_flags:", ltos(r)

        time.sleep(1)
        n = n + 1

    c.close_channel()


def test4():
    c = opencan(50000)    
    n = 0
    while (n < 10):
        f = "001801020304050607%02x" % n
        r = c.transmit_std(f)
        n = n + 1
    c.close_channel()



if __name__ == "__main__":
    if sys.platform=='win32':
        DEVICE = "COM5"
    else:
        DEVICE = "/dev/ttyUSB0"
    c = opencan(DEVICE, 250000)
    count = 0
    startTime = time.time()
    
    try:
        while (1):
            try:
                r = c.poll()
            except CANUSBError, e:
                # re-raise error if it's not timeout
                if str(e).find("timeout") < 0:
                    raise
            
            l = c.get_rxfifo_len()
            for i in range(0, l):
                f = c.get_rx_frame()
                print f
                count = count + 1
                
            if count > 10:
                strcount = str(i+count)
                databytes = map(ord, strcount)
                                
                f = CANMessage.CANFrame(102, 1, 0, len(databytes), tuple([b for b in databytes]))
                c.transmit_frame(f)
#            if count >= 500:
#                duration = time.time()-startTime
#                rate = float(count) / duration
#                print "received %d frames in %f s (%f frames/s)" % (count, duration, rate)
#                startTime = time.time()
#                count = 0;
    except KeyboardInterrupt:
        pass
    finally:
        c.close_channel()
