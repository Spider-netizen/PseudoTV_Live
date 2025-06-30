rd /s /q Z:\GitHub\PseudoTV_Live\plugin.video.pseudotv.live\

cd\
C:
cd\Program Files\TeraCopy
TeraCopy.exe Copy "Z:\portable_data\addons\plugin.video.pseudotv.live" Z:\GitHub\PseudoTV_Live\ /OverwriteAll

cd\
Z:
cd\GitHub\PseudoTV_Live
addon_generator.py

cd\
C:
cd\Program Files\TeraCopy
rd /s /q \\192.168.0.51\xbmc\portable_data\addons\plugin.video.pseudotv.live\
TeraCopy.exe Copy "Z:\GitHub\PseudoTV_Live\plugin.video.pseudotv.live" \\192.168.0.51\xbmc\portable_data\addons\ /OverwriteAll
rd /s /q \\192.168.0.123\internal\Android\data\org.xbmc.kodi\files\.kodi\addons\plugin.video.pseudotv.live\
TeraCopy.exe Copy "Z:\GitHub\PseudoTV_Live\plugin.video.pseudotv.live" \\192.168.0.123\internal\Android\data\org.xbmc.kodi\files\.kodi\addons\ /OverwriteAll
rd /s /q \\192.168.0.124\internal\Android\data\org.xbmc.kodi\files\.kodi\addons\plugin.video.pseudotv.live\
TeraCopy.exe Copy "Z:\GitHub\PseudoTV_Live\plugin.video.pseudotv.live" \\192.168.0.124\internal\Android\data\org.xbmc.kodi\files\.kodi\addons\ /OverwriteAll