import wx
import sys
import os
import CANController
from ConfigParser import RawConfigParser
from CANTxPanel import *
from CANRxPanel import *
from CANDatabasePanel import *


if sys.platform == "win32":
    serialports = ["COM1", "COM2", "COM3", "COM4", "COM5", "COM6", "COM7", "COM8", "COM9", "COM10", "COM11", "COM12"]
else:
    serialports = ["/dev/ttyUSB0", "/dev/ttyUSB1", "/dev/ttyUSB2", "/dev/ttyUSB3"]
CANBitsPerSec = [ "50000", "100000", "125000", "250000", "500000", "800000", "1000000" ]


class CANAnalyzerPanel(wx.Panel):
    def __init__(self, parent):
        wx.Panel.__init__(self, parent, -1)
        
        self.startButton = wx.Button(self, label="Start")
        self.startButton.Bind(wx.EVT_BUTTON, self.OnStart)
        
        self.stopButton = wx.Button(self, label="Stop")
        self.stopButton.Bind(wx.EVT_BUTTON, self.OnStop)
        self.stopButton.Enable(False)
                
        self.buttonBox = wx.BoxSizer(wx.HORIZONTAL)
        self.buttonBox.Add(self.startButton, flag=wx.EXPAND|wx.ALL, border=5)
        self.buttonBox.Add(self.stopButton, flag=wx.EXPAND|wx.ALL, border=5)
        
        self.parametersBox = wx.FlexGridSizer(rows=2, cols=2, hgap=5, vgap=5) 
        self.parametersBox.Add(wx.StaticText(self, label="Serial port"), border=0)
        self.serialPort = wx.Choice(self, choices=serialports)  
        self.serialPort.SetStringSelection(config.get("CANUSB", "SerialPort"))
        self.parametersBox.Add(self.serialPort, flag=wx.EXPAND|wx.ALL, border=0)
        self.parametersBox.Add(wx.StaticText(self, label="Speed"), border=0)
        self.speed = wx.Choice(self, choices=CANBitsPerSec)
        self.speed.SetStringSelection(config.get("CANUSB", "CANBitsPerSec"))
        self.parametersBox.Add(self.speed, flag=wx.EXPAND|wx.ALL, border=0)
               
        self.tabs = wx.Notebook(self)
        self.RxPanel = CANAnalyzerRxPanel(self.tabs)
        self.TxPanel = CANAnalyzerTxPanel(self.tabs)
        self.DbcPanel = CANDatabasePanel(self.tabs)
        
        self.tabs.AddPage(self.RxPanel, "RX")
        self.tabs.AddPage(self.TxPanel, "TX")
        self.tabs.AddPage(self.DbcPanel, "DataBase")
        
        self.vbox = wx.BoxSizer(wx.VERTICAL)
        self.vbox.Add(self.parametersBox, flag=wx.EXPAND|wx.ALL, border=5)
        self.vbox.Add(self.tabs, proportion=1, flag=wx.EXPAND|wx.ALL, border=0)
        self.vbox.Add(self.buttonBox, flag=wx.EXPAND|wx.ALL, border=5)
        
        self.SetSizer(self.vbox)   
        self.SetAutoLayout(True)
        
        self.can = None
            
    def OnStart(self, event):
        self.can = CANController.CANUSBController(self.serialPort.GetStringSelection(), int(self.speed.GetStringSelection()))
                
        self.can.Start(self.RxCallback)
        
        self.RxPanel.Start(self.can)
        self.TxPanel.Start(self.can)
        self.DbcPanel.Start(self.can)
        
        self.startButton.Enable(False)
        self.stopButton.Enable(True)
        
    # This callback is called asynchronously from a thread
    # that reads CAN frames. It posts an event to the UI
    # thread because the UI can only be safely updated in its own thread
    def RxCallback(self, numFrames):
        wx.PostEvent(self.RxPanel, FrameEvent(numFrames))
        
    def OnStop(self, event):
        self.RxPanel.Stop()
        self.TxPanel.Stop()
        self.DbcPanel.Stop()
        
        self.can.Stop()
                
        self.startButton.Enable(True)
        self.stopButton.Enable(False)        

    def CleanUp(self):
        config.set("CANUSB", "SerialPort", self.serialPort.GetStringSelection())
        config.set("CANUSB", "CANBitsPerSec", self.speed.GetStringSelection())
        
        if self.can != None:
            self.can.Stop()
        

class CANAnalyzerFrame(wx.Frame):
    def __init__(self, parent, ID, title, size):
        wx.Frame.__init__(self, parent, ID, title, wx.DefaultPosition, size)
        self.bkg = CANAnalyzerPanel(self) 
        self.Bind(wx.EVT_CLOSE, self.OnClose)
        
    def OnClose(self, event):
        self.bkg.CleanUp()
        event.Skip()
        
        
if __name__ == "__main__": 
    class CANAnalyzerApp(wx.App):
        def OnInit(self):
            win = CANAnalyzerFrame(parent=None, ID=-1, title="CAN Analyzer", size=(800, 600))
            win.Show(True)
            return True;
        
        def OnClose(self, event):
            event.Skip()
        
    config = RawConfigParser()
    configFilePath = os.path.join(os.getcwd(),"canalyzer.conf")
    confFiles = config.read(configFilePath)
    # Make sure all needed options are there
    if len(confFiles) == 0:
        config.add_section("CANUSB")
        
    if not config.has_option("CANUSB", "SerialPort"):
        config.set("CANUSB", "serialPort", serialports[0])
    if not config.has_option("CANUSB", "CANBitsPerSec"):
        config.set("CANUSB", "CANBitsPerSec", CANBitsPerSec[0])
        
    app = CANAnalyzerApp(0)     
    app.MainLoop()
    
    configFile = open(configFilePath, 'w')
    config.write(configFile)
    configFile.close()
    