'''
Created on Jun 10, 2009

@author: frederic
'''
import struct
import array
import math
import time

class CANFrame(object):
    def __init__(self, msg_id=0, xtd=0, rtr=0, ndata=0, data=() ):
        """
        msg_id -- Message ID (11 Bit or 29 Bit)
        xtd -- Extended 
        rtr -- Remote Transmission Request
        ndata -- Number of data bytes (0..8)
        data -- Sequence of ndata bytes
        """
        self.msg_id = msg_id
        self.rtr = rtr
        self.xtd = xtd
        self.ndata = ndata
        self.data = data # tuple with length 0..8
        self.timestamp = time.time()  # Timestamp of object creation
        
    def __str__(self):
        printdata = tuple(map(hex, self.data))
        return """Frame (%f): msg_id=0x%x xtd=%d rtr=%d ndata=%d data=%s""" % \
               (self.timestamp, self.msg_id, self.xtd, self.rtr, self.ndata, printdata) 
        
    def get_data(self):
        n = len(self.data)
        return self.data + (0,)*(8-n)

    def get_rtr(self):
        return self.rtr
    
    def get_xtd(self):
        return self.xtd

    def get_ndata(self):
        return self.ndata

    def get_msg_id(self):
        return self.msg_id
    
    def get_timestamp(self):
        return self.timestamp
    

class CANSignal(object):
    def __init__(self, name, id=0, xtd=0, dtype='u8', endian='intel', startbit=0, bitlength=32, val=0.0 ):
        """
        name -- Signal name
        id -- Signal arbitration ID (11 Bit or 29 Bit)
        xtd -- Specify whether signal uses a basic or extended frame
        dtype -- Data type (bit, u8, i8, u16, i16, u32, i32, u64, i64, f32, f64)
        endian -- Endianness (intel or motorola)
        startbit -- LSB position in the CAN frame payload
        bitlength -- Number of bits occupied by the signal
        val -- Signal value
        """
        self._name = name
        self._id = id
        self._xtd = xtd
        self._dtype = dtype
        self._endian = endian
        self._startbit = startbit
        self._bitlength = bitlength
        self._val = val
        
    def get_id(self):
        return self._id
    
    def get_xtd(self):
        return self._xtd
    
    def get_endian(self):
        return self._endian
    
    def get_dtype(self):
        return self._dtype
    
    def get_startbit(self):
        return self._startbit
    
    def get_bitlength(self):
        return self._bitlength
    
    def get_name(self):
        return self._name
    
    def get_val(self):
        #if not hasattr(self, "_val"):
        #    self._val = 0.0
        return self._val
    
    def to_canframe(self):
        bytes = ValueToRawData(self._dtype, self._endian, self._startbit, self._bitlength, self._val)   
        data = tuple([b for b in bytes])
        ndata = 8
        
        return CANFrame(self._id, self._xtd, 0, ndata, data)
    
    def from_canframe(self, frame):
        data = bytearray(frame.get_data())
        self._val = RawDataToValue(self._dtype, self._endian, self._startbit, self._bitlength, data)
        
        return self._val

def GetDataTypeSize(dataType):
    if dataType == "bit":
        return 1
    elif dataType == "u8":
        return 8  
    elif dataType == "i8":
        return 8  
    elif dataType == "u16":       
        return 16         
    elif dataType == "i16":       
        return 16         
    elif dataType == "u32":       
        return 32          
    elif dataType == "i32":       
        return 32          
    elif dataType == "u64":       
        return 64        
    elif dataType == "i64":       
        return 64       
    elif dataType == "f32":       
        return 32     
    elif dataType == "f64": 
        return 64

# Intel-stores the Most Significant Byte (MSB) first, i.e. the MSB is stored in the lowest memory location
#  Bit Progression from start bit: BitwiseLeft and BytewiseRight
# Motorola Forward-Most Significant Byte (MSB) is stored first, i.e. the MSB is stored in the lowest memory location
#  Bit Progression from start bit:BitwiseLeft,BytewiseLeft
# Motorola Backward-MSB is again stored first, but the start bit is counted from the rightmost byte. Hence, 
# the logical byte order is reversed or "backwards "when compared to Motorola Forwards
#  Bit Progression from start bit: BitwiseLeft,Bytewise Left
def ValueToRawData(dataType, endian, startBit, bitLength, value):
        
    if dataType == "bit":
        if value > 0.0:
            bytes = struct.pack("BBBBBBBB", 1, 0, 0, 0, 0, 0, 0, 0)
        else:
            bytes = struct.pack("BBBBBBBB", 0, 0, 0, 0, 0, 0, 0, 0)
    elif dataType == "u8":
        bytes = struct.pack("BBBBBBBB", int(math.floor(value+0.5))&0xFF, 0, 0, 0, 0, 0, 0, 0)
    elif dataType == "i8":
        bytes = struct.pack("bbbbbbbb", int(math.floor(value+0.5)), 0, 0, 0, 0, 0, 0, 0)
    elif dataType == "u16":       
        if endian == "motorola":
            bytes = struct.pack(">HHHH", int(math.floor(value+0.5))&0xFFFF, 0, 0, 0)          
        else:
            bytes = struct.pack("<HHHH", int(math.floor(value+0.5))&0xFFFF, 0, 0, 0)        
    elif dataType == "i16":       
        if endian == "motorola":
            bytes = struct.pack(">hhhh", int(math.floor(value+0.5)), 0, 0, 0)            
        else:
            bytes = struct.pack("<hhhh", int(math.floor(value+0.5)), 0, 0, 0)        
    elif dataType == "u32":       
        if endian == "motorola":
            bytes = struct.pack(">II", int(math.floor(value+0.5))&0xFFFFFFFF, 0)              
        else:
            bytes = struct.pack("<II", int(math.floor(value+0.5))&0xFFFFFFFF, 0)        
    elif dataType == "i32":       
        if endian == "motorola":
            bytes = struct.pack(">ii", int(math.floor(value+0.5)), 0)              
        else:
            bytes = struct.pack("<ii", int(math.floor(value+0.5)), 0)        
    elif dataType == "u64":       
        if endian == "motorola":
            bytes = struct.pack(">Q", int(math.floor(value+0.5)))              
        else:
            bytes = struct.pack("<Q", int(math.floor(value+0.5)))        
    elif dataType == "i64":       
        if endian == "motorola":
            bytes = struct.pack(">q", int(math.floor(value+0.5)))              
        else:
            bytes = struct.pack("<q", int(math.floor(value+0.5)))        
    elif dataType == "f32":       
        if endian == "motorola":
            bytes = struct.pack(">fi", value, 0)              
        else:
            bytes = struct.pack("<fi", value, 0)      
    elif dataType == "f64":        
        if endian == "motorola":
            bytes = struct.pack(">d", value)              
        else:
            bytes = struct.pack("<d", value)      
    
    tmp = struct.unpack("Q", bytes)[0]
     
    # shift converted data
    # We only support the "Motorola Forward case which is the one used in 
    # Candb++ databases (older Candb databases use Motorola Backward)
    lsbShift = 0
    if endian == "motorola":
        # add offset to original shift so that lsb of converted value
        # is at bit 0
        lsbShift = 8 - GetDataTypeSize(dataType)
    
    startBit = startBit + lsbShift    
    
    if startBit+bitLength > 64:
        bitLength = 64 - startBit
   
    if startBit < 0:
        mask = ((1L<<bitLength)-1) >> -startBit   
        tmp = (tmp >> -startBit) & mask
    else:
        mask = ((1L<<bitLength)-1) << startBit   
        tmp = (tmp << startBit) & mask
    
    bytes = struct.pack("Q", tmp)
    
    ret = []
    for byte in array.array('B', bytes):
        ret.append(byte)
        
    return ret

def RawDataToValue(dataType, endian, startBit, bitLength, rawBytes):
    bytes = array.array('B', rawBytes)

    tmp = struct.unpack("Q", bytes)[0]
    
    # shift converted data
    # We only support the "Motorola Forward case which is the one used in 
    # Candb++ databases (older Candb databases use Motorola Backward)
    lsbShift = 0
    if endian == "motorola":
        # add offset to original shift so that lsb of converted value
        # is at bit 0
        lsbShift = 8 - GetDataTypeSize(dataType)
    
    startBit = startBit + lsbShift    
    
    if startBit < 0:
        mask = ((1L<<bitLength)-1) >> -startBit
        tmp = (tmp & mask) << -startBit
    else:
        mask = ((1L<<bitLength)-1) << startBit
        tmp = (tmp & mask) >> startBit
    
    bytes = struct.pack("Q", tmp)
    
    if dataType == "bit":
        if tmp > 0:
            retval = 1
        else:
            retval = 0
    elif dataType == "u8":
        retval = struct.unpack("BBBBBBBB", bytes)[0]
    elif dataType == "i8":
        retval = struct.unpack("bbbbbbbb", bytes)[0]
    elif dataType == "u16":       
        if endian == "motorola":
            retval = struct.unpack(">HHHH", bytes)[0]              
        else:
            retval = struct.unpack("<HHHH", bytes)[0]  
    elif dataType == "i16":       
        if endian == "motorola":
            retval = struct.unpack(">hhhh", bytes)[0]              
        else:
            retval = struct.unpack("<hhhh", bytes)[0]             
    elif dataType == "u32":       
        if endian == "motorola":
            retval = struct.unpack(">II", bytes)[0]         
        else:
            retval = struct.unpack("<II", bytes)[0]  
    elif dataType == "i32":       
        if endian == "motorola":
            retval = struct.unpack(">ii", bytes)[0]         
        else:
            retval = struct.unpack("<ii", bytes)[0]     
    elif dataType == "u64":       
        if endian == "motorola":
            retval = struct.unpack(">Q", bytes)[0]            
        else:
            retval = struct.unpack("<Q", bytes)[0]   
    elif dataType == "i64":       
        if endian == "motorola":
            retval = struct.unpack(">q", bytes)[0]            
        else:
            retval = struct.unpack("<q", bytes)[0]        
    elif dataType == "f32":       
        if endian == "motorola":
            retval = struct.unpack(">fi", bytes)[0]              
        else:
            retval = struct.unpack("<fi", bytes)[0]   
    elif dataType == "f64":        
        if endian == "motorola":
            retval = struct.unpack(">d", bytes)[0]              
        else:
            retval = struct.unpack("<d", bytes)[0]      

    return retval


if __name__ == "__main__": 
    dataType = "f64"
    endian = "motorola"
    startBit = 56
    bitLength = 64
    for i in range(65535):
        orig_val = float(i/1000.0)
        rawData = ValueToRawData(dataType, endian, startBit, bitLength, orig_val)
        val = RawDataToValue(dataType, endian, startBit, bitLength, rawData)
        
        if orig_val != val:
            print "Error expected %f, got %f" % (orig_val, val)
            break
            
