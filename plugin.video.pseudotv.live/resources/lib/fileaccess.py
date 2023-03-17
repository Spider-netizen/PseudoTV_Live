#   Copyright (C) 2022 Lunatixz
#
#
# This file is part of PseudoTV Live.
#
# PseudoTV Live is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# PseudoTV Live is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with PseudoTV Live.  If not, see <http://www.gnu.org/licenses/>.
#
# -*- coding: utf-8 -*-

from globals    import *
from threading  import BoundedSemaphore, Timer

#info
ADDON_ID            = 'plugin.video.pseudotv.live'
REAL_SETTINGS       = xbmcaddon.Addon(id=ADDON_ID)
ADDON_NAME          = REAL_SETTINGS.getAddonInfo('name')
ADDON_VERSION       = REAL_SETTINGS.getAddonInfo('version')
ICON                = REAL_SETTINGS.getAddonInfo('icon')
FANART              = REAL_SETTINGS.getAddonInfo('fanart')
SETTINGS_LOC        = REAL_SETTINGS.getAddonInfo('profile')
ADDON_PATH          = REAL_SETTINGS.getAddonInfo('path')
LANGUAGE            = REAL_SETTINGS.getLocalizedString
COLOR_LOGO          = os.path.join(ADDON_PATH,'resources','skins','default','media','logo.png')

#constants 
DEFAULT_ENCODING           = "utf-8"
FILE_LOCK_MAX_FILE_TIMEOUT = 13
FILE_LOCK_NAME             = "FileLock.dat"

#variables
DEBUG_ENABLED       = REAL_SETTINGS.getSetting('Enable_Debugging').lower() == 'true'

def log(event, level=xbmc.LOGDEBUG):
    if not DEBUG_ENABLED and level != xbmc.LOGERROR: return #todo use debug level filter
    if level == xbmc.LOGERROR: event = '%s\n%s'%(event,traceback.format_exc())
    xbmc.log('%s-%s-%s'%(ADDON_ID,ADDON_VERSION,event),level)
    
class FileAccess:
    @staticmethod
    def open(filename, mode, encoding=DEFAULT_ENCODING):
        fle = 0
        log("FileAccess: trying to open %s"%filename)
        try: return VFSFile(filename, mode)
        except UnicodeDecodeError: return FileAccess.open(filename, mode, encoding)
        return fle


    @staticmethod
    def listdir(path):
        return xbmcvfs.listdir(path)


    @staticmethod
    def translatePath(path):
        return xbmcvfs.translatePath(path)


    @staticmethod
    def copy(orgfilename, newfilename):
        log('FileAccess: copying %s to %s'%(orgfilename,newfilename))
        dir, file = os.path.split(newfilename)
        if not FileAccess.exists(dir): FileAccess.makedirs(dir)
        return xbmcvfs.copy(orgfilename, newfilename)


    @staticmethod
    def move(orgfilename, newfilename):
        log('FileAccess: moving %s to %s'%(orgfilename,newfilename))
        if xbmcvfs.copy(orgfilename, newfilename):
            return xbmcvfs.delete(orgfilename)
        return False
        

    @staticmethod
    def delete(filename):
        return xbmcvfs.delete(filename)
        
        
    @staticmethod
    def exists(filename):
        try:
            return xbmcvfs.exists(filename)
        except UnicodeDecodeError:
            return os.path.exists(xbmcvfs.translatePath(filename))
        return False


    @staticmethod
    def openSMB(filename, mode, encoding=DEFAULT_ENCODING):
        fle = 0
        if os.name.lower() == 'nt':
            newname = '\\\\' + filename[6:]
            try:
                fle = codecs.open(newname, mode, encoding)
            except:
                fle = 0
        return fle


    @staticmethod
    def existsSMB(filename):
        if os.name.lower() == 'nt':
            filename = '\\\\' + filename[6:]
            return FileAccess.exists(filename)
        return False


    @staticmethod
    def rename(path, newpath):       
        log("FileAccess: rename %s to %s"%(path,newpath))
        if not FileAccess.exists(path):
            return False
        
        try:
            if xbmcvfs.rename(path, newpath):
                return True
        except Exception as e: 
            log("FileAccess: rename, Failed! %s"%(e), xbmc.LOGERROR)

        try:
            if FileAccess.move(path, newpath):
                return True
        except Exception as e: 
            log("FileAccess: move, Failed! %s"%(e), xbmc.LOGERROR)
           
        if path[0:6].lower() == 'smb://' or newpath[0:6].lower() == 'smb://':
            if os.name.lower() == 'nt':
                log("FileAccess: Modifying name")
                if path[0:6].lower() == 'smb://':
                    path = '\\\\' + path[6:]

                if newpath[0:6].lower() == 'smb://':
                    newpath = '\\\\' + newpath[6:]        
        
        if not os.path.exist(xbmcvfs.translatePath(path)):
            return False
        
        try:
            log("FileAccess: os.rename")
            os.rename(xbmcvfs.translatePath(path), xbmcvfs.translatePath(newpath))
            return True
        except Exception as e: 
            log("FileAccess: os.rename, Failed! %s"%(e), xbmc.LOGERROR)
 
        try:
            log("FileAccess: shutil.move")
            shutil.move(xbmcvfs.translatePath(path), xbmcvfs.translatePath(newpath))
            return True
        except Exception as e: 
            log("FileAccess: shutil.move, Failed! %s"%(e), xbmc.LOGERROR)

        log("FileAccess: OSError")
        raise OSError()


    @staticmethod
    def removedirs(path, force=True):
        if len(path) == 0: return False
        elif(xbmcvfs.exists(path)):
            return True
        try: 
            success = xbmcvfs.rmdir(dir, force=force)
            if success: return True
            else: raise
        except: 
            try: 
                os.rmdir(xbmcvfs.translatePath(path))
                if os.path.exists(xbmcvfs.translatePath(path)):
                    return True
            except: log("FileAccess: removedirs failed!")
            return False
            
            
    @staticmethod
    def makedirs(directory):
        try:  
            os.makedirs(xbmcvfs.translatePath(directory))
            return os.path.exists(xbmcvfs.translatePath(directory))
        except:
            return FileAccess._makedirs(directory)
            
            
    @staticmethod
    def _makedirs(path):
        if len(path) == 0:
            return False

        if(xbmcvfs.exists(path)):
            return True

        success = xbmcvfs.mkdir(path)
        if success == False:
            if path == os.path.dirname(xbmcvfs.translatePath(path)):
                return False

            if FileAccess._makedirs(os.path.dirname(xbmcvfs.translatePath(path))):
                return xbmcvfs.mkdir(path)
        return xbmcvfs.exists(path)


class VFSFile:
    def __init__(self, filename, mode):
        log("VFSFile: trying to open %s"%filename)
        if mode == 'w':
            if not FileAccess.exists(filename): 
                FileAccess.makedirs(os.path.split(filename)[0])
            self.currentFile = xbmcvfs.File(filename, 'wb')
        else:
            self.currentFile = xbmcvfs.File(filename, 'r')
        log("VFSFile: Opening %s"%filename, xbmc.LOGDEBUG)

        if self.currentFile == None:
            log("VFSFile: Couldnt open %s"%filename, xbmc.LOGERROR)


    def read(self, bytes=0):
        try:    return self.currentFile.read(bytes)
        except: return self.currentFile.readBytes(bytes)
        
        
    def readBytes(self, bytes=0):
        return self.currentFile.readBytes(bytes)
        

    def write(self, data):
        if isinstance(data,bytes):
            data = data.decode(DEFAULT_ENCODING, 'backslashreplace')
        return self.currentFile.write(data)
        
        
    def close(self):
        return self.currentFile.close()


    def seek(self, bytes, offset=1):
        return self.currentFile.seek(bytes, offset)


    def size(self):
        return self.currentFile.size()


    def readlines(self):
        return self.currentFile.read().split('\n')


    def tell(self):
        try:    return self.currentFile.tell()
        except: return self.currentFile.seek(0, 1)
        

class FileLock:
    def __init__(self):
        random.seed()        
        self.LOCK_LOC      = self.chkLOCK()
        self.lockedList    = []
        self.isExiting     = False
        self.lockFileName  = os.path.join(self.LOCK_LOC,FILE_LOCK_NAME)
        self.grabSemaphore = BoundedSemaphore()
        self.listSemaphore = BoundedSemaphore()
        log("FileLock: instance")


    def chkLOCK(self):
        LOCK_LOC = os.path.join(Settings().getSetting('User_Folder'))
        if not FileAccess.exists(LOCK_LOC):    
            if FileAccess.makedirs(LOCK_LOC):
                return LOCK_LOC
            LOCK_LOC = os.path.join(SETTINGS_LOC,'cache')
            if not FileAccess.exists(LOCK_LOC):    
                FileAccess.makedirs(LOCK_LOC)
                
        if not FileAccess.exists(FILE_LOCK_NAME):    
            FileAccess.open(FILE_LOCK_NAME,'a').close()
        return LOCK_LOC


    def close(self):
        log("FileLock: close")
        self.isExiting = True
        try: 
            if self.refreshLocksTimer.is_alive():   
                self.refreshLocksTimer.cancel()
                self.refreshLocksTimer.join()
        except: pass
        self.refreshLocksTimer = Timer(4.0, self.refreshLocks)
        self.refreshLocksTimer.name = "RefreshLocks"
        for item in self.lockedList:
            self.unlockFile(item)


    def refreshLocks(self):
        for item in self.lockedList:
            if self.isExiting:
                log("FileLock: IsExiting")
                return False
            self.lockFile(item, True)
            
        try: 
            if self.refreshLocksTimer.is_alive():
                self.refreshLocksTimer.cancel()
                self.refreshLocksTimer.join()
        except: pass
        self.refreshLocksTimer = Timer(4.0, self.refreshLocks)
        self.refreshLocksTimer.name = "RefreshLocks"
        if self.isExiting == False:
            self.refreshLocksTimer.start()
            return True
        return False


    def lockFile(self, filename, block = False):
        log("FileLock: lockFile %s"%filename)
        curval   = -1
        attempts = 0
        fle      = 0
        filename = filename.lower()
        locked   = True
        lines    = []

        while not xbmc.Monitor().abortRequested() and (locked == True and attempts < FILE_LOCK_MAX_FILE_TIMEOUT):
            locked = False
            if curval > -1:
                self.releaseLockFile()
                self.grabSemaphore.release()

            self.grabSemaphore.acquire()
            if self.grabLockFile() == False:
                self.grabSemaphore.release()
                return False

            try:
                fle = FileAccess.open(self.lockName, "r")
            except:
                log("FileLock: Unable to open the lock file")
                self.releaseLockFile()
                self.grabSemaphore.release()
                return False

            lines = fle.readlines()
            fle.close()
            val = self.findLockEntry(lines, filename)

            # If the file is locked:
            if val > -1:
                locked = True

                # If we're the ones that have the file locked, allow overriding it
                for item in self.lockedList:
                    if item == filename:
                        locked = False
                        block = False
                        break

                if curval == -1:
                    curval = val
                else:
                    if curval == val:
                        attempts += 1
                    else:
                        if block == False:
                            self.releaseLockFile()
                            self.grabSemaphore.release()
                            log("FileLock: File is locked")
                            return False

                        curval = val
                        attempts = 0

        log("FileLock: File is unlocked")
        self.writeLockEntry(lines, filename)
        self.releaseLockFile()
        existing = False

        for item in self.lockedList:
            if item == filename:
                existing = True
                break

        if existing == False:
            self.lockedList.append(filename)
            
        try: self.grabSemaphore.release()
        except: pass
        return True


    def grabLockFile(self):
        # Wait a maximum of 20 seconds to grab file-lock file.  This long
        # timeout should help prevent issues with an old cache.
        for i in range(40):
            # Cycle file names in case one of them is sitting around in the directory
            self.lockName = os.path.join(self.LOCK_LOC,'%s.lock'%(random.randint(1, 60000)))
            try:
                FileAccess.rename(self.lockFileName, self.lockName)
                fle = FileAccess.open(self.lockName, 'r')
                fle.close()
                return True
            except: 
                xbmc.Monitor().waitForAbort(0.5)

        log("FileLock: Creating lock file")
        try:
            fle = FileAccess.open(self.lockName, 'w')
            fle.close()
        except:
            log("FileLock: Unable to create a lock file")
            return False
        return True


    def releaseLockFile(self):
        log("FileLock: releaseLockFile")
        # Move the file back to the original lock file name
        try:
            FileAccess.rename(self.lockName, self.lockFileName)
        except:
            log("FileLock: Unable to rename the file back to the original name")
            return False
        return True


    def writeLockEntry(self, lines, filename, addentry = True):
        log("FileLock: writeLockEntry")
        # Make sure the entry doesn't exist.  This should only be the case
        # when the attempts count times out
        self.removeLockEntry(lines, filename)
        if addentry:
            try:
                lines.append("%s,%s\n"%((random.randint(1, 60000)),filename))
            except: return False

        try:    
            fle = FileAccess.open(self.lockName, 'w')
        except: 
            log("FileLock: Unable to open the lock file for writing")
            return False

        flewrite = ''
        for line in lines:
            flewrite += line

        try:    
            fle.write(flewrite)
        except: log("FileLock: Exception writing to the log file")
        fle.close()


    def findLockEntry(self, lines, filename):
        log("FileLock: findLockEntry")
        # Read the file
        for line in lines:
            # Format is 'random value,filename'
            index = line.find(",")
            flenme = ''
            setval = -1

            # Valid line, get the value and filename
            if index > -1:
                try:
                    setval = int(line[:index])
                    flenme = line[index + 1:].strip()
                except:
                    setval = -1
                    flenme = ''

            # The lock already exists
            if flenme == filename:
                log("FileLock: entry exists, val is %s"%(setval))
                return setval
        return -1


    def removeLockEntry(self, lines, filename):
        log("FileLock: removeLockEntry")
        realindex = 0
        for i in range(len(lines)):
            index = lines[realindex].find(filename)
            if index > -1:
                del lines[realindex]
                realindex -= 1
            realindex += 1


    def unlockFile(self, filename):
        log("FileLock: unlockFile %s"%filename)
        realindex = 0
        found     = False
        
        # First make sure we actually own the lock
        # Remove it from the list if we do
        self.listSemaphore.acquire()
        for i in range(len(self.lockedList)):
            if self.lockedList[realindex] == filename:
                del self.lockedList[realindex]
                found = True
                realindex -= 1
            realindex += 1

        self.listSemaphore.release()
        if found == False:
            log("FileLock: Lock not found")
            return False

        self.grabSemaphore.acquire()
        if self.grabLockFile() == False:
            self.grabSemaphore.release()
            return False

        try:
            fle   = FileAccess.open(self.lockName, "r")
            lines = fle.readlines()
            fle.close()
        except:
            log("FileLock: Unable to open the lock file")
            self.releaseLockFile()
            self.grabSemaphore.release()
            return False

        self.writeLockEntry(lines, filename.lower(), False)
        self.releaseLockFile()
        self.grabSemaphore.release()
        return True


    def isFileLocked(self, filename, block = False):
        log("FileLock: isFileLocked %s"%filename)
        self.grabSemaphore.acquire()
        if self.grabLockFile() == False:
            self.grabSemaphore.release()
            return True

        try:
            fle   = FileAccess.open(self.lockName, "r")
            lines = fle.readlines()
            fle.close()
        except:
            log("FileLock: Unable to open the lock file")
            self.releaseLockFile()
            self.grabSemaphore.release()
            return True

        retval = False
        if self.findLockEntry(lines, filename.lower()) > -1:
            retval = True

        self.releaseLockFile()
        self.grabSemaphore.release()
        return retval