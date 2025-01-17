import os, json, logging
import tagexplorer

logger = logging.getLogger(__name__)

TAG_SETS_PER_PAGE = 1000
TAGS_PER_PAGE = 1000
TAG_DATA_FILE = os.path.join(tagexplorer.base_dir, 'mediacloud-tags.json')

GEO_TAG_SET_NAME = "rahulb@media.mit.edu"


def geo_tag_set():
    results = tagexplorer.tags.all_tag_sets()
    tag_sets = [tag_set for tag_set in results if GEO_TAG_SET_NAME == tag_set['name']]
    return tag_sets[0]


def geo_tag_set_id():
    return geo_tag_set()['tag_sets_id']


def geo_tag(tags_id):
    tag_set = geo_tag_set()
    logger.debug("!!!! looking for "+str(tags_id))
    for tag in tag_set['tags']:
        if tag['tags_id'] == int(tags_id):
            return tag
    return None


def geonames_id_from_tag_name(tag_name):
    return tag_name[9:]


def story_count(tags_id):
    return tagexplorer.mc_server.story_count('tags_id_stories:{}'.format(tags_id))['count']


def all_tag_sets():
    """
    Return list of all tag sets, with tags under each
    """
    if os.path.isfile(TAG_DATA_FILE):
        logger.debug("Loading tag sets from "+TAG_DATA_FILE)
        json_data=open(TAG_DATA_FILE)
        data = json.load(json_data)
        return data
    # fetch all the tag sets
    logger.info("Fetching tag sets from MediaCloud:")
    tag_sets = []
    more_tag_sets_id = True
    max_tag_set = 0
    while more_tag_sets_id:
        logger.debug("  from "+str(max_tag_set))
        results = tagexplorer.mc_server.tagSetList(max_tag_set, TAG_SETS_PER_PAGE)
        tag_sets = tag_sets + results
        more_tag_sets_id = len(results)>0
        if len(results)>0:
            max_tag_set = results[-1]['tag_sets_id']
    logger.debug("  found "+str(len(tag_sets))+" sets")
    # now fill in all the tags
    for tag_set in tag_sets:
        logger.debug("Fetching tags in set "+str(tag_set['tag_sets_id']))
        tags = []
        more_tags = True
        max_tags_id = 0
        while more_tags:
            logger.debug(" from "+str(max_tags_id))
            results = tagexplorer.mc_server.tagList(tag_set['tag_sets_id'],max_tags_id,TAGS_PER_PAGE)
            #print json.dumps(results)
            tags = tags + results
            more_tags = len(results) > 0
            if len(results)>0:
                max_tags_id = results[-1]['tags_id']
        logger.debug("    found "+str(len(tags))+" tags in the set")
        tag_set['tags'] = tags
    # dump to a file
    with open(TAG_DATA_FILE, 'w') as outfile:
        json.dump(tag_sets, outfile)
        logger.info("Wrote tag sets to "+TAG_DATA_FILE)
    return tag_sets


def public_media_tag_sets():
    """
    Return list of all the public tag sets, with public tags under each
    """
    tag_sets = all_tag_sets()
    logger.debug("Finding just public data sets")
    tag_sets_to_remove = []
    for tag_set in tag_sets:
        #logger.debug("  looking into tag set '"+tag_set['name']+"' "+str(tag_set['tag_sets_id']))
        if tag_set['show_on_media'] in (0, None):
            logger.debug("  private - checking tags")
            removed_tag_count = 0
            tags_to_remove = []
            for tag in tag_set['tags']:
                if tag['show_on_media'] in (0, None):
                    tags_to_remove.append(tag)
                    #logger.debug("    removing tag '"+tag['tag']+"'"+str(tag['tags_id']))
            [tag_set['tags'].remove(tag) for tag in tags_to_remove]
            logger.debug("    removed "+str(removed_tag_count)+" tags")
        if len(tag_set['tags']) == 0:
            tag_sets_to_remove.append(tag_set)
    [tag_sets.remove(tag_set) for tag_set in tag_sets_to_remove]
    return tag_sets


# cache to reduce hits to mc server
tag_cache = {}  # id to tag


def tag(tags_id):
    if tags_id not in tag_cache:
        tag = tagexplorer.mc_server.tag(tags_id)
        tag_cache[tags_id] = tag
    return tag_cache[tags_id]

