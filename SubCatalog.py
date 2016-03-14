import urllib
import urllib.request
import time
import json
import re
import datetime
import logging
import logging.handlers

VERSION_STRING = 'Subreddit Cataloger v1.0 by /u/epiqlawlz\n'
USER_AGENT = 'Python/SubredditCataloger/1.0 (by /u/epiqlawlz)'

TITLE_RE = re.compile('^#.*$')          #Regex for detecting titles in catalog file
SUBREDDIT_RE = re.compile('^[\w]+$')    #Regex for detecting subreddits in catalog file
COMMENT_RE = re.compile('^\?.*$')
LOG_FILE_NAME = 'debug_log.txt'
MAX_DESCRIPTION_LENGTH = 50

VERY_HIGH_POPULARITY_MIN = datetime.timedelta(days=1)   #Minimum average ages for top 4 ranks
HIGH_POPULARITY_MIN = datetime.timedelta(days=3)        #'Very Low' is anything less than low.
AVERAGE_POPULARITY_MIN = datetime.timedelta(days=7)     #
LOW_POPULARITY_MIN = datetime.timedelta(days=21)        #


def getjson(url):   #Function for getting json data
    time.sleep(2)
    z = urllib.request.Request(url, data=None, headers={'User-Agent' : USER_AGENT})
    result = urllib.request.urlopen(z)
    result = json.loads(result.read().decode('utf-8'))
    return result

#Setting up the errror logger
logformatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger('SubCataloger')
logger.setLevel(logging.DEBUG)
handler = logging.handlers.RotatingFileHandler(
              LOG_FILE_NAME, maxBytes=10*1024*1024, backupCount=2)
handler.setFormatter(logformatter)
logger.addHandler(handler)
logger.info('Script started')

errorcount = 0

#Ready
print(VERSION_STRING)

#Load the catalog file
print('Reading catalog from file...')
try:
    with open ("catalog.txt", "r") as catalogfile:
        catalog=catalogfile.readlines()
except FileNotFoundError:
    print('Catalog file not found! Unable to continue')
    input('')
    quit()

#Empty the output file
open('output.txt', 'w').close()

#Itterate through the catalog
begintable = True
try:
    with open('output.txt', 'a') as outputfile:
        linecounter = 0
        for x in catalog:
            linecounter += 1
            x = x.strip()
            if len(x) == 0 or COMMENT_RE.match(x) != None: #If blank line or comment, ignore
                continue
            
            #If is a title listing... 
            elif TITLE_RE.match(x) != None:
                print('Scanning ' + x[2:].strip() + '(TITLE)...')
                outputfile.write('\n{0}  \n'.format(x[2:].strip()))
                begintable = True
                continue
            
            #If is a subreddit listing...
            elif SUBREDDIT_RE.match(x) != None:
                print('Scanning ' + x + '(SUBREDDIT)...')
                try:
                    aboutpage = getjson('http://www.reddit.com/r/{0}/about/.json'.format(x))      #Get subreddit about page
                    frontpage = getjson('http://www.reddit.com/r/{0}/.json?limit=100'.format(x))  #Get subreddit front page
                except Exception as e:
                    if str(e) == 'HTTP Error 403: Forbidden':
                        print('Requested subreddit "{0}" private, quarantined or gold-only, skipping...'.format(x))
                        logger.error('Requested subreddt /r/{0} inaccessable: 403 Forbidden'.format(x))
                        errorcount +=1
                        continue
                    elif str(e) == 'HTTP Error 404: Not Found':
                        print('The requested subreddit /r/{0} does not exist or has been banned, skipping...'.format(x))
                        logger.error('Requested subreddt /r/{0} inaccessable: 404 Not Found'.format(x))
                        errorcount +=1
                        continue 
                    else:
                        logger.exception(e)
                        raise
                
                try:
                    subcount = aboutpage['data']['subscribers']
                except KeyError:
                        print('The requested subreddit /r/{0} does not exist, skipping...'.format(x))
                        logger.error('Requested subreddt /r/{0} inaccessable: Key Error "subscribers"'.format(x))
                        errorcount +=1
                        continue

                subtitle = (aboutpage['data']['title'][:MAX_DESCRIPTION_LENGTH] + '..') if len(aboutpage['data']['title']) > MAX_DESCRIPTION_LENGTH else aboutpage['data']['title']
                activeaccounts = aboutpage['data']['accounts_active']
                
                #Start building the table
                if begintable:
                    outputfile.write('\nName----------------------- | Sub Count------ | Activity--------- | Activity Rank | Description----------------------------------------  \n')
                    outputfile.write('-|-:|:-:|:-:|-  \n')
                begintable = False
                subname = '/r/' + x
                
                #Remove stickied posts from count
                newpostlist = [x for x in frontpage['data']['children'] if not x['data']['stickied']]

                #Calculate average score and comment count
                averagescore = 0
                averagecomments = 0
                subpopularity = "[Very Low](/VL "")"
                creationdates = []
                if not len(frontpage['data']['children']) == 0:
                    for x in frontpage['data']['children']:
                        averagescore += x['data']['score']
                        averagecomments += x['data']['num_comments']
                        creationdates.append((int(x['data']['created_utc'])))
                    averagescore = averagescore // len(frontpage['data']['children'])
                    averagecomments = averagecomments // len(frontpage['data']['children'])
                    averagecreationdate = sum(creationdates) // len(creationdates)
                    averageage = datetime.datetime.utcnow() - datetime.datetime.fromtimestamp(averagecreationdate)
                    if (averageage < VERY_HIGH_POPULARITY_MIN):
                        subpopularity = '[Very High](/VH "")'
                    elif (averageage < HIGH_POPULARITY_MIN):
                        subpopularity = '[High](/H "")'
                    elif (averageage < AVERAGE_POPULARITY_MIN):
                        subpopularity = '[Average](/A "")'
                    elif (averageage < LOW_POPULARITY_MIN):
                        subpopularity = '[Low](/L "")'

                activitynumbers = "{0}/{1}/{2}".format(averagescore, averagecomments, activeaccounts)
                outputfile.write('{0} | {1} | {2} | {3} | {4} \n'.format(subname, subcount, activitynumbers, subpopularity, subtitle))
                
            else:
                logger.warning('Garbage on line {0} of catalog, skipping...'.format(linecounter))
                print('Garbage on line {0} of catalog, skipping...'.format(linecounter))
                errorcount +=1
                continue
    logger.info('Script terminated successfully')
    print('Successfully saved to output.txt, encountered {0} errors in catalog'.format(errorcount))
    input('Press enter to exit')
except Exception as e:
    logger.exception(e)
    raise

        
        
        
    
    
    
