# -*- coding: utf_8 -*-
import sys
import watchdog
from watchdog.events import RegexMatchingEventHandler,FileSystemMovedEvent
import logging

class CogimixEventHandler(RegexMatchingEventHandler):

    def __init__(self,cogimix):
        super(CogimixEventHandler, self).__init__([r"(^(.*)\.(mp3|ogg|mp4))$"],[],True)
        self._cogimix = cogimix
        self._logger = logging.getLogger('Cogimix')

    def dispatch(self, event):
        if(event.event_type != watchdog.events.EVENT_TYPE_MOVED  or event.src_path is not None ):
            e = event
        else:
            e = FileSystemMovedEvent('',event.dest_path,event.is_directory)
        super(CogimixEventHandler, self).dispatch(e)
               
    def on_created(self,event):
        super(CogimixEventHandler, self).on_created(event)
        self._logger.debug("File created !")
        self._cogimix.add(event.src_path);

    def on_modified(self,event):
        super(CogimixEventHandler, self).on_modified(event)
        self._cogimix.update(event.src_path);
        
    def on_deleted(self,event):
        super(CogimixEventHandler, self).on_deleted(event)
        self._logger.debug("File removed !")
        self._cogimix.remove(event.src_path);
         
    def on_moved(self,event):
        super(CogimixEventHandler, self).on_moved(event)
        self._logger.debug("File moved !")
        self._cogimix.update_path(event.src_path,event.dest_path);
   
       

   
     
