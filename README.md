pycogimix
=========
Simple python (draft) app to serve your music to Cogimix.com

Dependencies :  
* >=python 2.6
* watchdog
* cherrypy
* mutagen

Install :

```pip install mutagen cherrypy watchdog```

Usage:

Copy cogimix.conf.dist to cogimix.conf, edit the config file

```python pycogimix.py -c cogimix.conf```
