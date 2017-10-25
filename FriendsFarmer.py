import string, pymongo, os, time
from twython import Twython
from collections import Counter
from pymongo import MongoClient
from environment import api_key, user_to_collect

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
		print(key + " - " + str(len(search_data['statuses'])))
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
		print(slug['slug'] + " - " + str(len(users_by_slug['users'])))
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
			print("Private User - " + follower['screen_name'])
			continue
		followers_list = twitter.get_followers_list(screen_name=follower['screen_name'],
													count='200',
													skip_status=True,
													include_user_entities=False,
													cursor=cursor)
		ctr += 1
		# TODO : Fix get_followers_list[2]. Adjust according to rate limit.
		if ctr%15 == 0:
			time.sleep(1000)
		followers_of_follower.extend(followers_list['users'])
		print(follower['screen_name'] + " - " + str(len(followers_of_follower)) + " - " + str(ctr))
		for i in followers_of_follower:
			users.append({
							'username':	i['screen_name'],
							'_id': i['id_str']
						})
	append_to_db(users)

def follow_users():
	users = db['users_to_follow'].find({})
	count = 0
	for user in users:
		try:
			twitter.create_friendship(screen_name=user['username'],follow=True)
			count += 1
		except Exception as e:
			print("Can't follow " + user['username'])
			continue
		else:
			break
		finally:
			db['users_to_follow'].remove({'_id':user['_id']})
			if count%100==0:
				time.sleep(600)
			elif count%10==0:
				time.sleep(120)

if __name__ == '__main__':
	try:
		collect_suggested_users()
		time.sleep(1000)
		collect_similar_interests()
		time.sleep(1000)
		collect_followers_of_followers()
		time.sleep(1000)
		follow_users()
	except Exception as e:
		print(e)
		time.sleep(1000)
		follow_users()
