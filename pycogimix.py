#!/usr/bin/env python
# -*- coding: utf_8 -*-
import cherrypy
import mimetypes
from cherrypy.lib.static import serve_file
import logging
import CogimixEventHandler
import cogimix
import json
from watchdog.observers import Observer
from watchdog.observers.polling import PollingObserver
import os,sys
import argparse


def get_logging_lvl(x):
    return {
        'debug': logging.DEBUG,
        'info': logging.INFO,
        'warning': logging.WARNING,
        'error': logging.ERROR,
        }.get(x, logging.INFO) 

class CogimixServer:
    
    def search(self, query=None):
        if query == None :
            cl = cherrypy.request.headers['Content-Length']
            rawbody = cherrypy.request.body.read(int(cl))
            query = json.loads(rawbody)
            song_query = query['song_query']
        else:
            song_query = query
        resultDb = cogimixMusicProvider.search(song_query)
        return json.dumps(list([dict(r) for r in resultDb]))

    search.exposed = True

    def ping(self):
        result = cogimixMusicProvider.count_rows()
        if result:
            count = dict(result)
            return json.dumps(count)
        return json.dumps({})
    ping.exposed = True
    
    def get(self, id):
        result = cogimixMusicProvider.get_by_id(id)
        if result :
            track = dict(result)
            print mimetypes
            mime = mimetypes.guess_type(track['filepath'])[0]
            if mime:
                return serve_file(track['filepath'], mime)
            return serve_file(track['filepath'])
    get.exposed = True
    
def parse_args(config):
    parser = argparse.ArgumentParser(description='Start Cogimix music provider')
    parser.add_argument('-c','--config', help='Config file', type=str, required = True)
    parser.add_argument('-p','--port', help='HTTP listen port', type=int) 
    args = parser.parse_args()
    if  os.path.isfile(args.config):
        execfile(args.config,config)
        for key in [ 'server_port', 'db_file', 'log_level','music_folders','auth_mode' ]:
            if key not in config:
                print "Missing configuration entry : '{0}'".format(key)
                sys.exit()
        if config['auth_mode'] == 'none' or config['auth_mode'] == 'digest' or config['auth_mode'] == 'basic':
            if config['auth_mode'] != 'none':
                for key in [ 'auth_config', 'userpassdict' ]:
                    if key not in config:
                        print "Missing configuration entry : '{0}'".format(key)
                        sys.exit()
                for key in [ 'realm' ]:
                    if key not in config['auth_config'][config['auth_mode']]:
                        print "Missing configuration entry : '{0}' for {1} authentication".format(key,config['auth_mode'])
                        sys.exit()
                if config['auth_mode'] == 'digest':
                    if 'key' not in config['auth_config'][config['auth_mode']]:
                        print "Missing configuration entry : 'key' for {0} authentication".format(config['auth_mode'])
                        sys.exit()                   
        else:
            print "Unknown value for 'auth_mode' : {0} ('none', 'digest' or 'basic'".format(config['auth_mode'])
            sys.exit()
    else:
        print "Can't open the config file {0}".format(args.config)
        sys.exit()
    if args.port:
        config['server_port'] = args.port
        
if __name__ == "__main__":
    
    config = {}
    parse_args(config)
    logger = logging.getLogger('Cogimix')
    logger.setLevel(get_logging_lvl(config['log_level']))
    ch = logging.StreamHandler()
    ch.setLevel(logging.DEBUG)
    formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s -  %(message)s")
    ch.setFormatter(formatter)
    logger.addHandler(ch)
    if 'log_file' in config and config['log_file']:
        fh = logging.FileHandler(config['log_file'])
        fh.setFormatter(formatter)
        logger.addHandler(fh)
     
    cogimixMusicProvider = cogimix.CogimixMusicProvider(config['db_file'])

    event_handler = CogimixEventHandler.CogimixEventHandler(cogimixMusicProvider)
    for music_path in config['music_folders']:
        if os.path.isdir(music_path['path']) :
            observer = Observer()
            #observer = PollingObserver()
            observer.schedule(event_handler, path=music_path['path'], recursive=music_path['recursive'])
            observer.start()
            crawl_thread = cogimix.CrawlThread(cogimixMusicProvider, music_path['path'], music_path['recursive'])
            logger.debug("Start crawler for {0}".format(music_path['path']))
            crawl_thread.start()
        else:
            logger.error("Path '{0}' is not a directory or does not exist".format(music_path['path']))
    # authentication configuration
    auth_config = {}
    if(config['auth_mode'] == 'digest'):
        get_ha1 = cherrypy.lib.auth_digest.get_ha1_dict_plain(config['userpassdict'])
        auth_config = {'tools.auth_digest.on': True,
                       'tools.auth_digest.realm': config['auth_config']['digest']['realm'],
                       'tools.auth_digest.get_ha1': get_ha1,
                       'tools.auth_digest.key':  config['auth_config']['digest']['key'],
        }
    elif config['auth_mode'] == 'basic':
        checkpassword = cherrypy.lib.auth_basic.checkpassword_dict(config['userpassdict'])
        auth_config = { 'tools.auth_basic.on': True,
                        'tools.auth_basic.realm': config['auth_config']['basic']['realm'],
                        'tools.auth_basic.checkpassword': checkpassword,
                      }
    
    # server port
    cherrypy.server.socket_port = config["server_port"] if 'server_port' in config else 8000
    
    # start cherrypy
    cherrypy.quickstart(CogimixServer(), '/', config={'/' : auth_config})
    cogimixMusicProvider.refresh_from_db()
