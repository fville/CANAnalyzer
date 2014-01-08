'''
Created on Jun 12, 2009

@author: frederic
'''

import wx
import CANController
import CANDatabase

class CANAnalyzerTxPanel(wx.Panel):
    def __init__(self, parent):
        wx.Panel.__init__(self, parent)
        
        self.canSignalListBox = wx.BoxSizer(wx.VERTICAL)
        self.canSignalListBox.Add(wx.StaticText(self, label="Select signal(s) to send") , flag = wx.EXPAND)
        self.canSignalList = wx.CheckListBox(self, choices=[])
        self.canSignalList.Bind(wx.EVT_LISTBOX, self.OnCANSignalSelect)
        self.canSignalListBox.Add(self.canSignalList, proportion=1, flag=wx.EXPAND|wx.ALL)
        
        self.canSignalRateBox = wx.BoxSizer(wx.VERTICAL)
        self.canSignalRateBox.Add(wx.StaticText(self, label="Signal/s") , flag = wx.EXPAND)
        self.canSignalRate = wx.SpinCtrl(self, value="100")
        self.canSignalRate.SetRange(0, 2000)
        self.canSignalRateBox.Add(self.canSignalRate)
        
        self.vbox = wx.BoxSizer(wx.VERTICAL)
        self.vbox.Add(self.canSignalListBox, proportion=1, flag=wx.EXPAND|wx.ALL, border=5)
        self.vbox.Add(self.canSignalRateBox, proportion=1, flag=wx.EXPAND|wx.ALL, border=5)
        
        self.SetSizer(self.vbox)   
        self.SetAutoLayout(True)
        
        CANDatabase.candb.AddListener(self.OnCANDbUpdated)
        self.can = None
        
    def OnCANSignalSelect(self, event):
        pass
    
    def OnCANDbUpdated(self, signals):
        self.canSignalList.Clear()
        for sig in signals:
            self.canSignalList.Append(sig.get_name())
        
    def Start(self, can):
        self.can = can
        
        schedFrames = [] 
        
        # Send selected CAN frames to scheduler
        for i in range(0,self.canSignalList.GetCount()):
            if self.canSignalList.IsChecked(i):
                sig = CANDatabase.candb.FindSignalByName(self.canSignalList.GetString(i))
                if sig != None:
                    schedFrames.append(sig.to_canframe())
                    
        self.can.ScheduleFrames(schedFrames)                   
        
    def Stop(self):
        self.can = None 
