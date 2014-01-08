'''
Created on Jun 12, 2009

@author: frederic
'''
import wx
import CANMessage
import os
import CANDatabase

class ArrayCtrl(wx.Panel):
    def __init__(self, parent, numElements, style):
        wx.Panel.__init__(self, parent)
        
        self.sizer = wx.BoxSizer(style)
        self.elements = []
        
        for i in range(numElements):
            self.elements.append(wx.TextCtrl(self, value="",size=(35,-1)))
            elementSizer = wx.BoxSizer(wx.VERTICAL)
            elementSizer.Add(wx.StaticText(self, label="%d" % i))
            elementSizer.Add(self.elements[i])
            self.sizer.Add(elementSizer)
            
        self.SetSizer(self.sizer)
            
    def SetValue(self, index, value):
        if index < len(self.elements):
            self.elements[index].SetValue(value)
            
    def GetValue(self, index, value):
        rval = ""
        if index < len(self.elements):
            rval = self.elements[index].GetValue()
        return rval
    
    def SetValues(self, values):
        n = len(self.elements)
        if len(values) < n:
            n = len(values)
        for i in range(n):
            self.elements[i].SetValue(values[i])
            
    def GetValues(self):
        rval = []
        for i in range(len(self.elements)):
            rval.append(self.elements[i].GetValue())
        return rval
       
# Inherits wx.Window instead of wx.Panel to get focus events
class CANMessagePanel(wx.Panel):
    def __init__(self, parent, index):
        wx.Panel.__init__(self, parent)
        
        self.dataTypesVal=[ "bit", "i8", "u8", "i16", "u16", "i32", "u32", "f32", "f64" ]
        self.endianessesVal=[ "Intel" , "Motorola" ]
                
        self.index = index
        self.vsizer = wx.StaticBoxSizer(wx.StaticBox(self, label="Message #%d" % index), wx.VERTICAL)
                
        self.nameBox = wx.BoxSizer(wx.VERTICAL)
        self.nameBox.Add(wx.StaticText(self, label="Name") , flag = wx.EXPAND)
        self.name = wx.TextCtrl(self, value="Message %d" % index, size=(40,-1))
        self.nameBox.Add(self.name) 
        
        self.arbIdBox = wx.BoxSizer(wx.VERTICAL)
        self.arbIdBox.Add(wx.StaticText(self, label="Arb. ID") , flag = wx.EXPAND)
        self.arbId = wx.TextCtrl(self, value="0x0",size=(40,-1))
        self.arbIdBox.Add(self.arbId) 
        
        self.xtd = wx.CheckBox(self, label="Ext.")
        
        self.dataTypeBox = wx.BoxSizer(wx.VERTICAL)
        self.dataTypeBox.Add(wx.StaticText(self, label="Data Type") , flag = wx.EXPAND)
        self.dataType = wx.Choice(self, choices=self.dataTypesVal)
        self.dataType.SetSelection(2)
        self.dataType.Bind(wx.EVT_CHOICE, self.OnDataTypeChange)
        self.dataTypeBox.Add(self.dataType) 
        
        self.endianessBox = wx.BoxSizer(wx.VERTICAL)
        self.endianessBox.Add(wx.StaticText(self, label="Format") , flag = wx.EXPAND)
        self.endianess = wx.Choice(self, choices=self.endianessesVal)
        self.endianess.SetSelection(0)
        self.endianess.Bind(wx.EVT_CHOICE, self.OnEndiannessChange)
        self.endianessBox.Add(self.endianess)
        
        self.startBitBox = wx.BoxSizer(wx.VERTICAL)
        self.startBitBox.Add(wx.StaticText(self, label="Start bit (0-63)") , flag = wx.EXPAND)
        self.startBit = wx.SpinCtrl(self, value="0",size=(60,-1))
        self.startBit.SetRange(0,63)
        self.startBit.Bind(wx.EVT_SPINCTRL, self.OnStartBitChange)
        self.startBitBox.Add(self.startBit)  
        
        self.bitLengthBox = wx.BoxSizer(wx.VERTICAL)
        self.bitLengthBox.Add(wx.StaticText(self, label="Length (1-64 bits)") , flag = wx.EXPAND)
        self.bitLength = wx.SpinCtrl(self, value="8",size=(60,-1))
        self.bitLength.SetRange(1,64)
        self.bitLength.Bind(wx.EVT_SPINCTRL, self.OnBitLengthChange)
        self.bitLengthBox.Add(self.bitLength)  
        
        self.valueBox = wx.BoxSizer(wx.VERTICAL)
        self.valueBox.Add(wx.StaticText(self, label="Value") , flag = wx.EXPAND)
        self.value = wx.TextCtrl(self, value="0",size=(80,-1),style=wx.TE_PROCESS_ENTER)
        self.value.Bind(wx.EVT_TEXT_ENTER, self.OnValueChange)
        self.valueBox.Add(self.value) 
        
        self.rawBytesBox = wx.BoxSizer(wx.VERTICAL)
        self.rawBytesBox.Add(wx.StaticText(self, label="Raw bytes") , flag = wx.EXPAND)
        self.rawBytes = ArrayCtrl(self, 8, wx.HORIZONTAL)
        self.rawBytesBox.Add(self.rawBytes) 
             
        self.hsizer = wx.BoxSizer(wx.HORIZONTAL)
        self.hsizer.Add(self.nameBox, flag=wx.ALL, border=5) 
        self.hsizer.Add(self.arbIdBox, flag=wx.ALL, border=5) 
        self.hsizer.Add(self.xtd, flag=wx.ALL, border=5) 
        self.hsizer.Add(self.dataTypeBox, flag=wx.ALL, border=5) 
        self.hsizer.Add(self.endianessBox, flag=wx.ALL, border=5) 
        self.hsizer.Add(self.startBitBox, flag=wx.ALL, border=5) 
        self.hsizer.Add(self.bitLengthBox, flag=wx.ALL, border=5) 
        self.hsizer.Add(self.valueBox, flag=wx.ALL, border=5)
        
        self.vsizer.Add(self.hsizer)
        self.vsizer.Add(self.rawBytesBox, flag=wx.ALL, border=5) 
        
        self.SetSizer(self.vsizer)      
                
        self.dataTypesVal = [ w.lower() for w in self.dataTypesVal] 
        self.endianessesVal = [ w.lower() for w in self.endianessesVal] 
        
        self.UpdateRawBytes()
        
        self.Bind(wx.EVT_CHILD_FOCUS, self.OnChildFocus)
            
    def UpdateRawBytes(self):
        dType = self.dataTypesVal[self.dataType.GetSelection()]
        endian = self.endianessesVal[self.endianess.GetSelection()]
        startBit = self.startBit.GetValue()
        bitLength = self.bitLength.GetValue()
        value = float(self.value.GetValue())
        bytes = CANMessage.ValueToRawData(dType, endian, startBit, bitLength, value)
        rawBytes = ["0x%x" % b for b in bytes]
        self.rawBytes.SetValues(rawBytes)
        
    def OnDataTypeChange(self, event):
        self.UpdateRawBytes()
        
    def OnEndiannessChange(self, event):
        self.UpdateRawBytes()
        
    def OnValueChange(self, event):
        self.UpdateRawBytes()
        
    def OnStartBitChange(self, event):
        self.UpdateRawBytes()
        
    def OnBitLengthChange(self, event):
        self.UpdateRawBytes()
        
    def OnChildFocus(self, event):
        # notify parent that this message has the focus
        self.GetParent().SetSelectedMessage(self)
        
        # re-pain background using the system highlighting color
        self.SetBackgroundColour(wx.SystemSettings_GetColour(wx.SYS_COLOUR_HIGHLIGHT))
        self.Refresh()
        
    def Deselect(self):
        self.SetBackgroundColour(wx.SystemSettings_GetColour(wx.SYS_COLOUR_MENU))
        self.Refresh()
        self.UpdateRawBytes()
            
    def GetValue(self):
        name = self.name.GetValue()
        id = int(self.arbId.GetValue(),16)
        xtd = self.xtd.GetValue()
        dType = self.dataTypesVal[self.dataType.GetSelection()]
        endian = self.endianessesVal[self.endianess.GetSelection()]
        startBit = self.startBit.GetValue()
        bitLength = self.bitLength.GetValue()
        value = float(self.value.GetValue())
                
        return CANMessage.CANSignal(name, id, xtd, dType, endian, startBit, bitLength, value)
      
    def SetValue(self, message):
        self.name.SetValue(message.get_name())
        self.arbId.SetValue("0x%x" % message.get_id())
        self.xtd.SetValue(message.get_xtd())
        self.dataType.SetSelection(self.dataTypesVal.index(message.get_dtype().lower()))
        self.endianess.SetSelection(self.endianessesVal.index(message.get_endian().lower()))
        self.startBit.SetValue(message.get_startbit())
        self.bitLength.SetValue(message.get_bitlength())
        self.value.SetValue("%f" % message.get_val())       
        
        
class CANMessageListPanel(wx.ScrolledWindow):
    def __init__(self, parent):
        wx.ScrolledWindow.__init__(self, parent, -1, wx.Point(0,0))   
        self.SetScrollRate(0,10) 
        
        self.Messages = []
        self.SelectedMessage = -1 
        
        self.sizer = wx.BoxSizer(wx.VERTICAL)    
        self.SetSizerAndFit(self.sizer)  
        
    def AddMessage(self, val=None):
        self.Messages.append(CANMessagePanel(self, len(self.Messages)))
        self.sizer.Add(self.Messages[-1], proportion=0, flag=wx.EXPAND|wx.ALL)
        if val != None:
            self.Messages[-1].SetValue(val)
        self.FitInside() 
        
    def RemoveMessage(self, index):
        # if index < 0, remove currently selected message
        if index < 0:
            index = self.SelectedMessage
        
        if index >= 0:
            msg = self.Messages[index]
            self.sizer.Remove(msg)
            self.RemoveChild(msg)
            self.Messages.remove(msg)
            msg.Destroy()
            del msg
            self.FitInside()
                    
    def SetSelectedMessage(self, panel):
        # De-select previously selected message
        if self.SelectedMessage >= 0:
            self.Messages[self.SelectedMessage].Deselect()
            
        self.SelectedMessage = self.Messages.index(panel)
        
    def GetSelectedMessage(self):
        if self.SelectedMessage < 0:
            return None
        
        return self.Messages[self.SelectedMessage]
    
    def GetMessage(self, index):
        if index >= len(self.Messages):
            return None
        
        return self.Messages[index]  
    
    def Clear(self):
        del self.Messages[:]     
        self.sizer.Clear()
        self.FitInside()
           
        
class CANDatabasePanel(wx.Panel):
    def __init__(self, parent):
        wx.Panel.__init__(self, parent)
            
        self.MessageList = CANMessageListPanel(self)
                                    
        self.addButton = wx.Button(self, label="Add Frame")
        self.addButton.Bind(wx.EVT_BUTTON, self.OnAdd)
        
        self.removeButton = wx.Button(self, label="Remove Frame")
        self.removeButton.Bind(wx.EVT_BUTTON, self.OnRemove)
        
        self.loadDbButton = wx.Button(self, label="Load Database")
        self.loadDbButton.Bind(wx.EVT_BUTTON, self.OnLoadDatabase)
        
        self.saveDbButton = wx.Button(self, label="Save Database")
        self.saveDbButton.Bind(wx.EVT_BUTTON, self.OnSaveDatabase)
        
        self.sendMessageButton = wx.Button(self, label="Send Message")
        self.sendMessageButton.Bind(wx.EVT_BUTTON, self.OnSendMessage)
        self.sendMessageButton.Enable(False)
                
        self.buttonBox = wx.BoxSizer(wx.HORIZONTAL)
        self.buttonBox.Add(self.addButton, flag=wx.CENTER|wx.ALL, border=5)
        self.buttonBox.Add(self.removeButton, flag=wx.CENTER|wx.ALL, border=5)
        self.buttonBox.Add(self.loadDbButton, flag=wx.CENTER|wx.ALL, border=5)
        self.buttonBox.Add(self.saveDbButton, flag=wx.CENTER|wx.ALL, border=5)
        self.buttonBox.Add(self.sendMessageButton, flag=wx.CENTER|wx.ALL, border=5)
          
        self.box = wx.BoxSizer(wx.VERTICAL)
        self.box.Add(self.MessageList, proportion=1, flag=wx.EXPAND|wx.ALL)
        self.box.Add(self.buttonBox, proportion=0, flag=wx.EXPAND|wx.ALL)
        self.SetSizer(self.box)
        
        self.can = None
        
    def Start(self, can):
        self.can = can 
        self.sendMessageButton.Enable(True)
        
    def Stop(self):
        self.sendMessageButton.Enable(False)
        self.can = None 
        
    def OnAdd(self, event):
        self.MessageList.AddMessage()
            
    def OnRemove(self, event):
        self.MessageList.RemoveMessage(-1)
    
    def OnLoadDatabase(self, event):
        dbPath = wx.FileSelector(message = "Choose a CAN database file", default_path=os.getcwd())
        
        messages = CANDatabase.candb.Load(dbPath)
        self.MessageList.Clear()
        for msg in messages:
            self.MessageList.AddMessage(msg)
                    
    def OnSaveDatabase(self, event):
        dlg = wx.FileDialog(parent = self, message = "Choose a CAN database file", style=wx.FD_SAVE|wx.FD_OVERWRITE_PROMPT|wx.FD_CHANGE_DIR, defaultDir=os.getcwd())
        if dlg.ShowModal() != wx.ID_OK:
            return  
        dbPath=dlg.GetPath()
        
        # get all CAN messages in list
        i = 0
        messages=[]
        while 1:
            messagePane = self.MessageList.GetMessage(i)
            if not messagePane:
                break
            messages.append(messagePane.GetValue())
            i=i+1
                
        CANDatabase.candb.Save(dbPath, messages)
        
    def OnSendMessage(self, event):
        msg = self.MessageList.GetSelectedMessage().GetValue()
        self.can.SendFrames(None, [msg.to_canframe()])
    
