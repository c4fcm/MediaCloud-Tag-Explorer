import os, sys, time, json, logging, ConfigParser, pymongo, locale
from operator import itemgetter
from flask import Flask, render_template

parentdir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0,parentdir) 
import mediacloud
import mediacloud.api
from mcexamples.db import ExampleMongoStoryDatabase

app = Flask(__name__)

cache = {}  # in-memory cache, controlled by _get_from_cache and _set_in_cache helpers

# setup logging
logging.basicConfig(filename='mc-server.log',level=logging.DEBUG)
log = logging.getLogger('mc-server')
log.info("---------------------------------------------------------------------------")

# connect to the database
config = ConfigParser.ConfigParser()
config.read(parentdir+'/mc-client.config')
try:
    db = ExampleMongoStoryDatabase(config.get('db','name'),config.get('db','host'),int(config.get('db','port')))
except pymongo.errors.ConnectionFailure, e:
    log.error(e)
else:
    log.info("Connected to "+config.get('db','name')+" on "+config.get('db','host')+":"+str(config.get('db','port')))

@app.route("/")
def index():
    media_source_info = _get_from_cache('media_source_info',3600) # cache lasts one hour
    if media_source_info == None:
        story_counts_by_media_id = db.storyCountByMediaId()
        top_media_sources = []
        media_info_json = []
        for media_id in story_counts_by_media_id.keys():
            clean_id = str(int(media_id))
            top_media_sources.append({
                'id': int(media_id),
                'clean_id': str(int(media_id)),
                'name': _media_name(media_id),
                'story_count': story_counts_by_media_id[media_id]
            })
            media_info_json.append({
                'id': int(media_id),
                'story_count': int(story_counts_by_media_id[media_id]),
                'value': _media_name(media_id),
            })
        _set_in_cache('media_source_info',{'top_media_sources':top_media_sources, 'media_source_info':media_source_info})        
    else:
        top_media_sources = media_source_info['top_media_sources']
        media_info_json = media_source_info['media_source_info']
    story_count = db.storyCount()
    return render_template("base.html",
        story_count = story_count,
        english_story_pct = int(round(100*db.englishStoryCount()/story_count)),
        top_media_sources = sorted(top_media_sources,key=itemgetter('story_count'), reverse=True)[0:40],
        media_info_json = json.dumps(media_info_json),
        max_story_id = db.getMaxStoryId()
    )

@app.route("/media/all/info")
def all_domain_info():
    reading_level_info = _get_from_cache('reading_level_info',86400) # cache lasts one day
    if reading_level_info == None:
        reading_level_info = _reading_level_info()
        _set_in_cache('reading_level_info',reading_level_info)
    return render_template("data.js",
        reading_level_info = reading_level_info
    )

@app.route("/media/<media_id>/info")
def domain_info(media_id):
    return render_template("data_for_media_source.js",
        media_name = _media_name(media_id),
        story_count = db.storyCountForMediaId(media_id),
        reading_level_info = _reading_level_info(media_id)
    )

def _media_name(media_id):
    return mediacloud.api.mediaSource(int(media_id))['name']

def _reading_level_info(domain=None, items_to_show=20):
    data = db.storyReadingLevelFreq(domain)
    return _assemble_info(data,1,items_to_show)

def _assemble_info(data,bucket_size,items_to_show):
    values = []
    for key in sorted(data.iterkeys()):
        values.append(data[key])
    values = values[:items_to_show]
    return {'values': values,
            'values_json': json.dumps(values),
            'final_bucket': bucket_size*items_to_show,
            'items_to_show': items_to_show,
            'biggest_value': max(values)
    }

def _get_from_cache(key, max_age):
    if key in cache:
        if time.mktime(time.gmtime()) - cache[key]['time'] < max_age:
            return cache[key]['value']
    return None

def _set_in_cache(key, value):
    cache[key] = {
        'value': value,
        'time': time.mktime(time.gmtime())
    }

def format_number(value):
    try:
        locale.setlocale(locale.LC_ALL, 'en_US.UTF-8') #use locale.format for commafication
    except locale.Error:
        locale.setlocale(locale.LC_ALL, '') #set to default locale (works on windows)
    return locale.format('%d', value, True)
    #return "${0:,d}".format(int(value))

if __name__ == "__main__":
    app.debug = True
    app.jinja_env.filters['prettynumberformat'] = format_number
    app.run()
