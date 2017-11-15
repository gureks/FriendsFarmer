import pytz
import time
from twython import Twython
from pymongo import MongoClient
from environment import api_key, user_to_collect, threshold_for_inout_ratio
from datetime import datetime

'''
	TODO : Fix line #99 and #120
	TODO : Add datetime to requirements.txt
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

def append_to_db(users, name):
	# Add to database
	for i in users:
		db[name].update({'_id':i['_id']}, i, True)
	print(db[name].count({}))

def collect_followers():
	followers = list()
	cursor = -1
	ctr = 0

	# Store all followers in a db
	while cursor!=0:
		followers_list = twitter.get_followers_list(screen_name=user_to_collect,
													count='200',
													skip_status=True,
													include_user_entities=False,
													cursor=cursor)
		for follower in followers_list['users']:
			followers.append({
				'username':	follower['screen_name'],
				'_id': follower['id_str']
			})

		cursor = followers_list['next_cursor']

		ctr += 1
		if ctr%15==0:
			print ('Sleeping for 900 seconds')
			time.sleep(900)

	print ('Collected all ' + str(len(followers)) + ' followers. Storing them in the db')
	append_to_db(followers, 'followers')

def collect_following():
	following = list()
	ctr = 0
	cursor = -1
	# Store all friends in a db
	while cursor!=0:
		friends_list = twitter.get_friends_list(screen_name=user_to_collect,
													count='200',
													skip_status=True,
													include_user_entities=False,
													cursor=cursor)

		for friend in friends_list['users']:
			following.append({
				'username':	friend['screen_name'],
				'_id': friend['id_str']
			})

		cursor = friends_list['next_cursor']

		ctr += 1
		if ctr%15==0:
			print ('Sleeping for 900 seconds')
			time.sleep(900)

	print ('Collected all ' + str(len(following)) + ' friends. Storing them in the db')
	append_to_db(following, 'following')

def friends_to_unfollow():
	following = db['following'].find({}, no_cursor_timeout=True)
	followers = db['followers'].find({}, no_cursor_timeout=True)

	unfollow = list()

	month = {'Jan' : 1, 'Feb' : 2, 'Mar' : 3, 'Apr' : 4, 'May' : 5, 'Jun' : 6, 'Jul' : 7, 'Aug' : 8, 'Sep' : 9, 'Oct' : 10, 'Nov' : 11, 'Dec' : 12}
	# To be changed
	last_date = datetime(2017, 5, 1, 00, 00, 00)

	# Code pasand nahi aaya
	followers_usernames = []
	for follower in followers:
		followers_usernames.append(follower['username'])

	c = 1
	for friend in following:
		user_name = friend['username']
		print(user_name)
		# Check if someone we follow don't follow us back
		if user_name in followers_usernames:
			continue
		else:
			if c%850==0:
				append_to_db(unfollow, 'users_to_unfollow')
				print ('Sleeping for 1000 seconds')
				time.sleep(1000)
			try:
				result = twitter.show_user(user_id=friend['_id'], include_entities=True)
				c += 1
			except Exception as e:
				print (user_name + str(e))
				unfollow.append({
					'_id': friend['_id'],
					'username':	friend['username']
				})
				continue
			else:
				pass
			finally:
				pass

			if result['protected']:
				print('Private User - ' + user_name)
				unfollow.append({
					'_id': friend['_id'],
					'username':	friend['username']
				})
				continue

			if not result['statuses_count']:
				print (user_name + ' added to unfollowing list cause of inactivity.')
				unfollow.append({
					'_id': friend['_id'],
					'username':	friend['username']
				})
				continue

			if 'status' not in result.keys():
				print (user_name + ' added to unfollowing list cause of inactivity.')
				unfollow.append({
					'_id': friend['_id'],
					'username':	friend['username']
				})
				continue

			latest_tweet = result['status']['created_at']
			latest_tweet_dt = datetime.strptime(latest_tweet, '%a %b %d %X %z %Y')

			num_friends = result['friends_count']
			num_followers = result['followers_count']

			# Check if the last tweet is done before threshold last date
			if latest_tweet_dt < last_date.replace(tzinfo=pytz.UTC):
				print (user_name + ' added to unfollowing list since his last tweet was done at ' + str(latest_tweet_dt.date()))
				unfollow.append({
					'_id': friend['_id'],
					'username':	friend['username']
				})

			elif float(num_followers)/(num_friends+1) > threshold_for_inout_ratio:
				print (user_name + ' added to unfollowing list since his in/out ratio was ' +str(float(num_followers)/(num_friends+1)))
				unfollow.append({
					'_id': friend['_id'],
					'username':	friend['username']
				})

	append_to_db(unfollow, 'users_to_unfollow')

def unfollow_users():
	users = db['users_to_unfollow'].find({}, no_cursor_timeout=True)
	count = 0
	for user in users:
		try:
			twitter.destroy_friendship(screen_name=user['username'])
			print('Unfollowed ' + user['username'])
			count += 1
		except Exception as e:
			print(e)
			print("Can't unfollow " + user['username'])
		else:
			pass
		finally:
			db['users_to_unfollow'].remove({'_id':user['_id']})
			db['following'].remove({'_id':user['_id']})
			if count%100==0:
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
		collect_followers()
		print('Followers collected... Sleeping 1000 seconds')
		time.sleep(1000)
		collect_following()
		print('Following collected... Sleeping 1000 seconds')
		time.sleep(1000)
		friends_to_unfollow()
		print('Filter applied... Sleeping 1000 seconds')
		time.sleep(1000)
		unfollow_users()
		print('Unfollowed... Exiting...')
	except Exception as e:
		print(e)
		time.sleep(1000)
		unfollow_users()
		print('Unfollowed... Exiting...')
