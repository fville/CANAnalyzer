'''
Created on Jun 12, 2009

@author: frederic
'''
import wx
import sys
import CANController
import CANDatabase
import time

# define incoming CAN frame notification event
EVT_FRAME_ID = wx.NewId()

def EVT_FRAME(win, func):
    win.Connect(-1, -1, EVT_FRAME_ID, func)
    
class FrameEvent(wx.PyEvent):
    def __init__(self, data):
        wx.PyEvent.__init__(self)
        self.SetEventType(EVT_FRAME_ID)
        self.data = data
        

# Sub-class ListCtrl to create a virtual list control
# that can dynamically fetch its content without
# storing it in memory
class FrameList(wx.ListCtrl):
    def __init__(self, parent):
        wx.ListCtrl.__init__(self, parent, -1, 
            style=wx.LC_REPORT|wx.LC_VIRTUAL)
        self.parent = parent
        self.oneFramePerID = False
        
    def SetOneFramePerID(self, val):
        self.oneFramePerID = val
        
    def GetOneFramePerID(self):
        return self.oneFramePerID
        
    def UpdateFrameCount(self, numFrames):
        self.SetItemCount(numFrames)
        self.EnsureVisible(numFrames-1)

    def OnGetItemText(self, item, col):
        if self.oneFramePerID:
            f = self.parent.GetLastCANFrameByID(item)
        else:
            f = self.parent.GetCANFrame(item)
            
        if 0 == col:
            return "%d" % item
        elif 1 == col:
            return str(f.get_timestamp())
        elif 2 == col:
            return "0x%08x" % f.get_msg_id()
        elif 3 == col:
            return "%d" % f.get_xtd()
        elif 4 == col:
            return "%d" % f.get_rtr()
        elif 5 == col:
            return "%d" % f.get_ndata()
        elif 6 == col:
            return "0x%02x 0x%02x 0x%02x 0x%02x 0x%02x 0x%02x 0x%02x 0x%02x" % f.get_data()
        else:
            # Find if there is a CAN signal for this id
            sig = CANDatabase.candb.FindSignalById(f.get_msg_id())
            if sig != None:
                value = sig.from_canframe(f)
                return str(value)
            return ""
            

    def OnGetItemImage(self, item):
        pass

    def OnGetItemAttr(self, item):
        return None


class CANAnalyzerRxPanel(wx.Panel):
    def __init__(self, parent):
        wx.Panel.__init__(self, parent)
        
        self.ShowOneMessagePerID = wx.CheckBox(self, label="Show one line per message ID")
        self.ShowOneMessagePerID.Bind(wx.EVT_CHECKBOX, self.OnShowOneMessage)
        
        self.receivedMsgs = FrameList(self)
        self.receivedMsgs.InsertColumn(0, "", width=60)
        self.receivedMsgs.InsertColumn(1, "Timestamp", width=80)
        self.receivedMsgs.InsertColumn(2, "ID", width=100)
        self.receivedMsgs.InsertColumn(3, "Ext.", width=20)
        self.receivedMsgs.InsertColumn(4, "RTR", width=20)
        self.receivedMsgs.InsertColumn(5, "Length", width=50)
        self.receivedMsgs.InsertColumn(6, "Bytes", width=300)
        self.receivedMsgs.InsertColumn(7, "Value", width=200)
        
        self.receivedMsgs.Bind(wx.EVT_LIST_ITEM_SELECTED, self.OnItemSelected)
        self.receivedMsgs.Bind(wx.EVT_LIST_ITEM_ACTIVATED, self.OnItemActivated)
        self.receivedMsgs.Bind(wx.EVT_LIST_ITEM_DESELECTED, self.OnItemDeselected)
        
        self.msgRateList = wx.ListCtrl(self, style=wx.LC_REPORT)
        self.msgRateList.InsertColumn(0, "ID", width=100)
        self.msgRateList.InsertColumn(1, "Count", width=100)
        self.msgRateList.InsertColumn(2, "Rate (msg/s)", width=100)
        
        self.clearButton = wx.Button(self, label="Clear")
        self.clearButton.Bind(wx.EVT_BUTTON, self.OnClear)
                
        self.vbox = wx.BoxSizer(wx.VERTICAL)
        self.vbox.Add(self.ShowOneMessagePerID, flag=wx.CENTER|wx.ALL, border=5)
        self.vbox.Add(self.receivedMsgs, proportion=1, flag=wx.EXPAND|wx.ALL, border=5)
        self.vbox.Add(self.msgRateList, proportion=0, flag=wx.EXPAND|wx.ALL, border=5)
        self.vbox.Add(self.clearButton, flag=wx.CENTER|wx.ALL, border=5)
        
        self.SetSizer(self.vbox)   
        self.SetAutoLayout(True)
        
        EVT_FRAME(self, self.OnFrameReceived)   
        
        self.can = None
        self.starttime = 0.0
        
    def Start(self, can):
        self.can = can 
        self.starttime = time.clock()
        
    def Stop(self):
        pass
        #self.can = None 
        
    # Event handler for the CAN frame receive event
    def OnFrameReceived(self, event):
        if event.data !=  None:
            # Update the frame list control with the total number
            # of frames to display. The list control is virtual
            # and will dynamically fetch the frames that are visible
            if self.receivedMsgs.GetOneFramePerID():
                self.receivedMsgs.UpdateFrameCount(len(self.can.GetLastFramesByID()))
            else:
                self.receivedMsgs.UpdateFrameCount(event.data)
            
            # Update frame rate list with the latest frame counts
            self.msgRateList.DeleteAllItems()
            frameCounts = self.can.GetFrameCounts()
            for id, count in frameCounts.items():
                index = self.msgRateList.InsertStringItem(sys.maxint, "0x%08x" % id)
                self.msgRateList.SetStringItem(index, 1, str(count))
                rate = count/(time.clock()-self.starttime)
                self.msgRateList.SetStringItem(index, 2, str(rate))
                
    def OnClear(self, event):
        self.can.ClearFrames()
        self.receivedMsgs.UpdateFrameCount(0)
        self.receivedMsgs.DeleteAllItems()
        self.msgRateList.DeleteAllItems()
        
    def OnShowOneMessage(self, event):     
        if self.ShowOneMessagePerID.IsChecked():
            if(self.can):  
                self.receivedMsgs.UpdateFrameCount(len(self.can.GetLastFramesByID()))
            self.receivedMsgs.SetOneFramePerID(True)
        else:
            if(self.can):  
                self.receivedMsgs.UpdateFrameCount(self.can.GetTotalFrameCount())
            self.receivedMsgs.SetOneFramePerID(False)
        
    def OnItemSelected(self, event):
        self.currentItem = event.m_itemIndex
    
    def OnItemActivated(self, event):
        self.currentItem = event.m_itemIndex
    
    def OnItemDeselected(self, event):
        pass
    
    def GetCANFrame(self, index):
        return self.can.GetFrame(index)
    
    def GetLastCANFrameByID(self, index):
        return self.can.GetLastFramesByID().values()[index]
        
            
