'''
Created on Jul 31, 2009

@author: frederic
'''
import CANMessage
import pickle
import os


class CANDatabase(object):
    def __init__(self):
        self._db={}
        self._listeners=[]
        
    def GetSignals(self):
        return self._db.items()
    
    def FindSignalById(self, id):
        if self._db.has_key(id):
            return self._db[id]
        return None
    
    def FindSignalByName(self, name):
        for sig in self._db.values():
            if name == sig.get_name():
                return sig
        return None
    
    # listeners are notified when the database is updated
    def AddListener(self, listener):
        self._listeners.append(listener)

    def Load(self, dbPath):
        signals = []
        if len(dbPath) > 0:
            # save message list to file using json format
            try:
                f = open(dbPath, "r")
                signals = pickle.load(f)
                f.close()
            except IOError, e:
                print "Can't open file " + dbPath + ". Error: " + e
            else:
                # replace global copy of database with version loaded from file
                self._db.clear()
                for sig in signals:
                    self._db[sig.get_id()]=sig
                    
                for l in self._listeners:
                    l(signals)
                    
        return signals
                        
    def Save(self, dbPath, signals):  
        # replace global copy of database with new version
        # about to be saved
        self._db.clear()
        for sig in signals:
            self._db[sig.get_id()]=sig
            
        for l in self._listeners:
            l(signals)
            
        if len(dbPath) > 0:            
            # save signal list to file 
            try:
                f = open(dbPath, "w")
                pickle.dump(signals, f)
                f.close()
            except IOError, e:
                print "Can't save file " + dbPath + ". Error: " + e
    

candb = CANDatabase()
