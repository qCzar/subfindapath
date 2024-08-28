#!/usr/bin/python
from __future__ import division
import sys
import praw
import time
import config
import logging
from datetime import datetime, date, timedelta
from prawcore.exceptions import RequestException
from operator import itemgetter
from logging.handlers import RotatingFileHandler


logger = logging.getLogger()
handler = logging.StreamHandler(sys.stdout)
formatter = logging.Formatter(
		'%(asctime)s %(levelname)-8s %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)
logger.setLevel(logging.INFO)
logging.getLogger('prawcore').setLevel(logging.ERROR)

# Reddit app API login creds
username = config.username
r = praw.Reddit(client_id=config.client_id, 
				client_secret=config.client_secret,
				user_agent=config.user_agent,
				username=config.username,
				password=config.password,
				timeout=60)

subname = config.subname
subreddit = r.subreddit(subname)
# Create list of sub moderators to ignore for flair
moderators = ["AutoModerator"]
try:
	for mod in subreddit.moderator():
	    moderators.append(mod.name)
except Exception as e:
	logging.error('Failed to load sub moderators' + str(e))
keywords = config.keywords
processed_comments = []


# Calculates the age in hours of a reddit submission
def get_age(post):
    t = datetime.now()
    utc_seconds = time.mktime(t.timetuple())
    hours = (utc_seconds - post.created_utc) / 60 / 60
    return hours


# Determines whether bot user has already replied to a reddit submission or comment
def replied(comment):
	replies = ""
	if hasattr(comment, "submission"):
		try:
			comment.refresh()
		except Exception as e:
			logging.info("Failed to refresh comment:" + str(e))
		replies = comment.replies
	else:
		replies = comment.comments

	if not replies:
		return False
	for reply in replies:
		if reply.author and reply.author.name.lower() == username.lower():
			return True
	return False


# Check if a user has been rewarded in the current thread
def awarded_in_thread(user, post):
	post.comments.replace_more(limit=None)
	for comment in post.comments.list():
		try:
			comment.refresh()
		except:
			logging.info("Failed to refresh comment: %s" % comment.permalink)
		if comment.author and comment.author.name == username and user.name in comment.body:
			return True
	return False


# Add one point to user flair, change rank text if needed
def increase_flair(user):
	rank_dict = config.flairs
	# Pull the user's flair. If it exists, increment it, otherwise use the
	# placeholder flair.
	user_flair_text = ""
	user_flair_class = ""
	new_flair_class = ""
	new_flair_text = ""
	new_flair_template = ""
	# Pull existing flair
	for flair in subreddit.flair(redditor=user, limit=None):
		user_flair_text = flair['flair_text']
	# If user has never won, give them the first flair
	if not user_flair_text:
		new_flair_text = rank_dict[1]['title'] + " [1]"
		new_flair_template = rank_dict[1]['template']
	elif user_flair_text:
		# Determine the rank # portion of the flair
		if "[" in user_flair_text:
			new_rank = int(user_flair_text.partition("[")[2].partition("]")[0]) + 1
		# Do not change rank of special flair user
		else: 
			logging.info("Skipping flair for special user %s" % user.name)
			return False
		# Determine the text portion based on the rank #
		rank_text = ""
		max_rank = 1
		for rank_value in rank_dict.keys():
			if new_rank >= rank_value:
				max_rank = rank_value
			else:
				break
		
		rank_text = rank_dict[max_rank]["title"]

		new_flair_text = rank_text + " [" + str(new_rank) + "]"
	

	logging.info("Setting {0:23} to {1:25}".format(user.name, new_flair_text))
	subreddit.flair.set(user.name, text=new_flair_text, flair_template_id=new_flair_template)

	return True


def process_comments():
	# "comment" refers to the "!helpful" comment
	# "award_comment" refers to the comment giving advice
	for comment in subreddit.stream.comments(skip_existing=True):
		# If a post is over 200 comments, lock it and leave a comment
		try:
			submission = comment.submission
			if submission.num_comments >= 200 and not replied(submission) and get_age(submission) <= 2000:
				logging.info("Locking 200+ comment post %s" % submission.shortlink)
				bot_comment = submission.reply("Your post has been popular! To keep post quality high, we limit posts to 200 comments. Please [message the moderators](https://www.reddit.com/message/compose/?to=/r/findapath) if you have any questions.")
				bot_comment.mod.distinguish()
				submission.mod.lock()
		except Exception as e:
			logging.error("Failed to lock 200 comment post %s %s" % (submission.shortlink, str(e)))

		# Ignore processed and not OP comments
		if comment.id in processed_comments \
		or not comment.is_submitter \
		or comment.is_root \
		or replied(comment):
			if comment.id not in processed_comments:
				processed_comments.append(comment.id)
			continue
		# Check if OP used keyword
		helpful = False
		for keyword in keywords:
			if keyword.lower() in comment.body.lower():
				helpful = True
				break
		if helpful:
			award_comment = comment.parent()
			# Don't flair OP or mods
			if award_comment.author.name in moderators \
				or award_comment.author.name == comment.author.name:
				continue
			logging.info("Detected trigger from %s to %s - %s" % (comment.author.name, award_comment.author.name, comment.submission.shortlink))
			# Check if already awarded in the thread
			if awarded_in_thread(award_comment.author, comment.submission):
				logging.info("Commenter %s already awarded in this thread %s" % (award_comment.author.name, comment.permalink))
				bot_comment = comment.reply("/u/%s has already been given a point in this post." % award_comment.author.name)
				bot_comment.mod.distinguish()
				continue
			
			flaired = increase_flair(award_comment.author)
			#logging.info("Awarding pt to %s - %s" % (award_comment.author, comment.submission.shortlink))
			if flaired:
				bot_comment = comment.reply(
					"Thank you for confirming that /u/%s has "
					"provided helpful advice for you. 1 point awarded." 
					% award_comment.author.name)
				bot_comment.mod.distinguish()
			processed_comments.append(comment.id)
			time.sleep(5)


# Return a summary of all user ranks
def get_score_summary():
	flairs = []
	ranks = []
	for flair in subreddit.flair(limit=None):
		if not flair['flair_text']:
			continue
		flair_text = flair.get('flair_text', '').partition("[")[0]
		flair_rank = flair.get('flair_text', '').partition("[")[2].partition("]")[0]
		if not flair_text:
			continue

		flairs.append(flair_text)
		if flair_rank.isdigit():
			ranks.append(flair_rank)

	for flair in sorted(set(flairs)):
		if flairs.count(flair) >= 1:
			print(flair, flairs.count(flair))

	for rank in sorted(set(ranks)):
		print(rank, "|", ranks.count(rank))


if __name__ == "__main__":
	logging.info("Started flair script")

	#############################################
	### If you want to print the rank report,   #
	### uncomment the next 2 lines and restart  #
	#get_score_summary()						#
	#exit(0)									#
	#############################################
	while True:
		try:
			process_comments()
		except Exception as e:
			logging.error(str(e))
			time.sleep(30)

# ---- message bot with "report" in subject line or body
# ----- bot sends PM with formatted report
