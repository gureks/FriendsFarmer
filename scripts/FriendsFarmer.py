import pytz
import time
from twython import Twython
from collections import Counter
from pymongo import MongoClient
from environment import api_key, user_to_collect, threshold_for_inout_ratio
from datetime import datetime

'''
	TODO : Fix Most_common. Adjust according to rate limit.
	TODO : Fix user_suggestions_by_slug. Adjust according to rate limit.
	TODO : Fix get_followers_list[1]. Adjust according to rate limit.
	TODO : Fix get_followers_list[2]. Adjust according to rate limit.
'''

connection = MongoClient()
db = connection['FriendsFarmer']

# Creating the Twython object
twitter = Twython(
	api_key['api_key'],
	api_key['api_secret'],
	api_key['access_token'],
	api_key['access_token_secret']
)

def append_to_db(users):
	# Add to database
	for i in users:
		db['users_to_follow'].update({'_id':i['_id']}, i, True)
	print(db['users_to_follow'].count({}))

def remove_from_db(users, collection):
	# Remove from database
	print('Initial ' + collection + ' size: ' + str(db[collection].count({})))
	for i in users:
		db[collection].remove({'_id':i})
	print('Updated ' + collection + 'size: ' + str(db[collection].count({})))

def collect_similar_interests():
	# Get the latest tweets of the user
	statuses = twitter.get_user_timeline(screen_name=user_to_collect,
											count='100',
											include_entities=True,
											include_rts=True,
											exclude_replies=False)
	hashtags = list()
	hashtags_count = Counter()

	# Get the most common hashtags
	for i in statuses:
		for j in i['entities']['hashtags']:
			hashtags.append(j['text'])
	hashtags_count.update(hashtags)

	# Get the top search result users of the above hashtags
	users = list()

	# TODO : Fix Most_common this. Adjust according to rate limit.
	for key, value in hashtags_count.most_common(800):
		search_data = twitter.search(q='#'+key,
										count='100',
										include_entities= True,
										result_type='popular',
										lang='en')
		print(key + ' - ' + str(len(search_data['statuses'])))
		for i in search_data['statuses']:
			users.append({
							'username':	i['user']['screen_name'],
							'_id': i['user']['id_str']
						})
	append_to_db(users)

def collect_suggested_users():
	# Access to Twitter’s list of suggested user categories.
	slugs = twitter.get_user_suggestions(lang='en')
	# TODO : Fix this. Adjust according to rate limit.
	slugs = slugs[:10]
	users = list()
	for slug in slugs:
		users_by_slug = twitter.get_user_suggestions_by_slug(slug=slug['slug'],
																lang='en')
		print(slug['slug'] + ' - ' + str(len(users_by_slug['users'])))
		for i in users_by_slug['users']:
			users.append({
							'username':	i['screen_name'],
							'_id': i['id_str']
						})
	append_to_db(users)

def collect_followers_of_followers():
	users = list()
	followers = list()
	cursor = -1
	ctr = 0
	# Collect current user's followers
	# TODO : Fix get_followers_list[1]. Adjust according to rate limit.
	while cursor!=0:
		followers_list = twitter.get_followers_list(screen_name=user_to_collect,
													count='200',
													skip_status=True,
													include_user_entities=False,
													cursor=cursor)
		ctr += 1
		cursor = followers_list['next_cursor']
		followers.extend(followers_list['users'])

	# Collect followers of the above collected followers
	for follower in followers:
		cursor = -1
		followers_of_follower = list()
		if follower['protected']:
			print('Private User - ' + follower['screen_name'])
			continue
		followers_list = twitter.get_followers_list(screen_name=follower['screen_name'],
													count='200',
													skip_status=True,
													include_user_entities=False,
													cursor=cursor)
		ctr += 1
		followers_of_follower.extend(followers_list['users'])
		print(follower['screen_name'] + ' - ' + str(len(followers_of_follower)) + ' - ' + str(ctr))
		for i in followers_of_follower:
			users.append({
							'username':	i['screen_name'],
							'_id': i['id_str']
						})
		if ctr%15 == 0:
			append_to_db(users)
			print('Sleeping 1000...')
			time.sleep(1000)
	append_to_db(users)

def follow_filter():
	users_to_follow = db['users_to_follow'].find({}, no_cursor_timeout=True)
	followers = db['followers'].find({}, no_cursor_timeout=True)

	remove = list()

	month = {'Jan' : 1, 'Feb' : 2, 'Mar' : 3, 'Apr' : 4, 'May' : 5, 'Jun' : 6, 'Jul' : 7, 'Aug' : 8, 'Sep' : 9, 'Oct' : 10, 'Nov' : 11, 'Dec' : 12}
	# To be changed
	last_date = datetime(2017, 1, 1, 00, 00, 00)

	followers_usernames = []
	for follower in followers:
		followers_usernames.append(follower['username'])

	c = 1
	for user in users_to_follow:
		user_name = user['username']
		print(user_name)

		if user_name in followers_usernames:
			continue
		else:
			if c%850==0:
				remove_from_db(remove, 'users_to_follow')
				print ('Sleeping for 1000 seconds')
				time.sleep(1000)
			try:
				result = twitter.show_user(user_id=user['_id'], include_entities=True)
				c+=1
			except Exception as e:
				print (user_name + str(e))
				remove.append(user['_id'])
				continue
			else:
				pass
			finally:
				pass

			if result['protected']:
				print('Private User - ' + user_name)
				remove.append(user['_id'])
				continue

			if not result['statuses_count']:
				print (user_name + ' added to unfollowing list cause of inactivity.')
				remove.append(user['_id'])
				continue

			if 'status' not in result.keys():
				print (user_name + ' added to unfollowing list cause of inactivity.')
				remove.append(user['_id'])
				continue

			latest_tweet = result['status']['created_at']
			latest_tweet_dt = datetime.strptime(latest_tweet, '%a %b %d %X %z %Y')

			num_friends = result['friends_count']
			num_followers = result['followers_count']

			# Check if the last tweet is done before threshold last date
			if latest_tweet_dt < last_date.replace(tzinfo=pytz.UTC):
				print (user_name + ' added to unfollowing list since his last tweet was done at ' + str(latest_tweet_dt.date()))
				remove.append(user['_id'])

			elif float(num_followers)/(num_friends+1) > threshold_for_inout_ratio:
				print (user_name + ' added to unfollowing list since his in/out ratio was ' +str(float(num_followers)/(num_friends+1)))
				remove.append(user['_id'])

	remove_from_db(remove, 'users_to_follow')

def follow_users():
	users = db['users_to_follow'].find({}, no_cursor_timeout=True)
	count = 0
	for user in users:
		try:
			twitter.create_friendship(screen_name=user['username'],follow=True)
			print('Followed ' + user['username'])
			count += 1
		except Exception as e:
			print("Can't follow " + user['username'])
			continue
		else:
			continue
		finally:
			db['users_to_follow'].remove({'_id':user['_id']})
			if count%950==0:
				print('Returning...')
				return
			elif count%100==0:
				print('Sleeping 1000 seconds')
				time.sleep(1000)
			elif count%50==0:
				print('Sleeping 500 seconds')
				time.sleep(500)
			elif count%10==0:
				print('Sleeping 250 seconds')
				time.sleep(250)
	users.close()

if __name__ == '__main__':
	try:
		collect_suggested_users()
		print('Suggested users collected... Sleeping 1000...')
		time.sleep(1000)
		collect_similar_interests()
		print('Similar interest users collected... Sleeping 1000...')
		time.sleep(1000)
		collect_followers_of_followers()
		print('Followers of follwers collected... Sleeping 1000...')
		time.sleep(1000)
		follow_filter()
		print('Follow filter applied... Sleeping 1000...')
		time.sleep(1000)
		follow_users()
	except Exception as e:
		print(e)
		time.sleep(1000)
		follow_users()
