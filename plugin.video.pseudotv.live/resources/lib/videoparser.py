#   Copyright (C) 2021 Jason Anderson, Lunatixz
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

from resources.lib.globals    import *
from resources.lib.parsers    import MP4Parser
from resources.lib.parsers    import AVIParser
from resources.lib.parsers    import MKVParser
from resources.lib.parsers    import FLVParser
from resources.lib.parsers    import TSParser
from resources.lib.parsers    import NFOParser
from resources.lib.parsers    import VFSParser
 
class VideoParser:
    def __init__(self):
        self.AVIExts   = ['.avi']
        self.MP4Exts   = ['.mp4', '.m4v', '.3gp', '.3g2', '.f4v', '.mov']
        self.MKVExts   = ['.mkv']
        self.FLVExts   = ['.flv']
        self.TSExts    = ['.ts', '.m2ts']
        self.STRMExts  = ['.strm']
        self.VFSPaths  = ['resource://','plugin://','upnp://','pvr://']


    def getVideoLength(self, filename, fileItem={}, jsonRPC=None):
        log("VideoParser: getVideoLength %s"%filename)
        if len(filename) == 0:
            log("VideoParser: getVideoLength, No file name specified")
            return 0

        if FileAccess.exists(filename) == False:
            log("VideoParser: getVideoLength, Unable to find the file")
            return 0

        base, ext = os.path.splitext(filename)
        ext = ext.lower()
        
        if filename.startswith(tuple(self.VFSPaths)):
            self.parser = VFSParser.VFSParser(fileItem, jsonRPC)
        elif ext in self.AVIExts:
            self.parser = AVIParser.AVIParser()
        elif ext in self.MP4Exts:
            self.parser = MP4Parser.MP4Parser()
        elif ext in self.MKVExts:
            self.parser = MKVParser.MKVParser()
        elif ext in self.FLVExts:
            self.parser = FLVParser.FLVParser()
        elif ext in self.TSExts:
            self.parser = TSParser.TSParser()
        elif ext in self.STRMExts:
            self.parser = NFOParser.NFOParser()
        else:
            log("VideoParser: getVideoLength, No parser found for extension %s"%(ext))
            return 0
            
        duration = int(self.parser.determineLength(filename))
        if duration == 0 and not filename.startswith(tuple(self.VFSPaths)):
            log("VideoParser: getVideoLength, Unable to find duration for %s, trying .nfo"%(ext))
            self.parser = NFOParser.NFOParser()
            duration = int(self.parser.determineLength(filename))
        log('VideoParser: getVideoLength, duration = %s'%(duration))
        return duration