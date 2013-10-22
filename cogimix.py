# -*- coding: utf_8 -*-
import sqlite3
import hashlib
import mutagen
import threading
import os
import re
import logging

class CogimixMusicProvider:

    
    def __init__(self, db_path):
        self._db = CogimixDb(db_path)
        self.create_db()
        self._regex_ext = re.compile(r'(^(.*)\.(mp3|ogg|mp4))$')
        self._logger = logging.getLogger('Cogimix')
    
    def create_db(self):
        self._db.write("""
         CREATE TABLE IF NOT EXISTS tracks (
        id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL ,
        title varchar(255) DEFAULT NULL,
        artist varchar(255) DEFAULT NULL,
        album varchar(255) DEFAULT NULL,
        md5 varchar(32) DEFAULT NULL,
        filepath text)
        """)
    
    def add(self, filepath):
        self._logger.info("Add : " + filepath)
        i = self.get_meta(filepath)
        if i:
            self._db.write("INSERT INTO tracks(title,artist,album,filepath,md5) VALUES (?, ?, ?, ?,?)", i)
          
    def update(self, filepath, skip_existing=False):
        
        if self.check_extension(filepath):
            self._logger.info('Update ' + filepath)
            result = self.get_by_path(filepath)
            if result :
                track = dict(result)
                self._logger.debug('Already in db, id : ' + str(track['id']))
                if skip_existing:
                    self._logger.debug('Skip this entry')
                    return
                self._logger.debug(track)
                meta = self.get_meta(filepath)
                if meta:
                    query = "UPDATE tracks SET title = ?,artist = ?,album = ?,filepath = ?, md5 = ? WHERE id = ?"
                    self._db.write(query, meta + (track['id'],))
            else:
                self.add(filepath)
                     
    def update_path(self, src_path, dest_path):
        self._logger.debug('update_path ' + src_path)
        if src_path != '' and src_path is not None:
            self.update(src_path)
        else:
            self.update(dest_path)
            
    def remove(self, filepath):
        """Remove track from db identified by filepath"""
        self._logger.debug('Delete ' + filepath)
        md5 = hashlib.md5(filepath).hexdigest()
        self._db.write("DELETE FROM tracks WHERE md5 = ?", (md5,))
   
               
    def is_file_present_in_db(self, filepath):
        return self._db.read('SELECT 1 FROM tracks WHERE filepath=?', (filepath,)).fetchone()
    
    def check_extension(self, filepath):
        """Check file extension (mp3 or ogg or mp4)"""
        if self._regex_ext.match(filepath):
            self._logger.debug('Extension match')
            return True
        self._logger.debug('Extension does not match')
        return False
        
        
    def get_meta(self, filepath):
        """Extract metadata from file with mutagen
           Return a tuple like (title,artist,album,filepath,md5(filepath))"""
        try:
            audio = mutagen.File(filepath, easy=True);
            if audio:
                self._logger.debug('Tag extracted')
                artist = audio.get("artist")
                if artist and len(artist) > 0 :
                    artist = artist[0]
                    
                title = audio.get("title")
                if title and len(title) > 0 :
                    title = title[0]
                    
                album = audio.get("album")
                if album and len(album) > 0 :
                    album = album[0]
                    
                return (title, artist, album, filepath, hashlib.md5(filepath).hexdigest())
            
        except Exception, e:
            self._logger.error(e)
        return None
    
    def crawl_dir(self, path, recursive=True, skip_existing=False):
        """Search in this path for music"""
        if recursive :
            for root, subFolders, files in os.walk(path):
                for file in files:
                    filepath = os.path.join(root, file)
                    self.update(filepath, skip_existing)
        else:
            for f in os.listdir(path):
                self.update(os.path.join(path, f), skip_existing)
    
    def refresh_from_db(self):
        """Verify if tracks in db exist in the file system."""
        query = "SELECT DISTINCT(filepath) FROM tracks"
        resultDb = self._db.read(query).fetchall()
        for track in [dict(r) for r in resultDb]:
            if not os.path.isfile(track['filepath']):
                self.remove(track['filepath'])
            
                
    def get_by_id(self, track_id):
        """Get one track from db by id."""
        query = "SELECT * FROM tracks WHERE id = ?"
        cursor = self._db.read(query, (track_id,))
        return cursor.fetchone()
        
    def count_rows(self):
        """Count total tracks in db."""
        query = "SELECT COUNT(*) as count FROM tracks"
        cursor = self._db.read(query)
        return cursor.fetchone()

         
    def get_by_path(self, path):
        """Get one track from db by filepath."""
        query = "SELECT * FROM tracks WHERE md5 = ?"
        cursor = self._db.read(query, (hashlib.md5(path).hexdigest(),))
        return cursor.fetchone()
        
    def search(self, song_query):
        """Search in db for tracks like song_query"""
        query = "SELECT * FROM tracks WHERE title LIKE ? OR artist LIKE ? OR album LIKE ?"
        param = "%" + song_query + "%"
        cursor = self._db.read(query, (param, param, param,))
        return cursor.fetchall()

class CrawlThread (threading.Thread):
   
        def __init__(self, cogimix_provider, path, recursive):
            super(CrawlThread, self).__init__()
            self._cogimix_provider = cogimix_provider
            self._path = path
            self._recursive = recursive
       
        def run (self):
            self._cogimix_provider.crawl_dir(self._path, self._recursive, True)
                    
class CogimixDb:
 
    def __init__(self, db_path):
        self.data_file = db_path
 
    def connect(self):
        self.conn = sqlite3.connect(self.data_file)
        self.conn.text_factory = lambda x: unicode(x, 'utf-8', 'ignore')
        self.conn.row_factory = sqlite3.Row
        return self.conn.cursor()
 
    def disconnect(self):
        self.cursor.close()
 
    def free(self, cursor):
        cursor.close()
 
    def write(self, query, values=''):
        cursor = self.connect()
        if values != '':
            cursor.execute(query, values)
        else:
            cursor.execute(query)
        self.conn.commit()
        return cursor
    
        
    def read(self, query, values=''):
        cursor = self.connect()
        if values != '':
            cursor.execute(query, values)
        else:
            cursor.execute(query)
        return cursor
