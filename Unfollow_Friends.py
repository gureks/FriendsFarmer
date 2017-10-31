import string, pymongo, os, time
from twython import Twython
from collections import Counter
from pymongo import MongoClient
from environment import api_key, user_to_collect
import datetime

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
		db['users_to_unfollow'].update({'_id':i['_id']}, i, True)
	print(db['users_to_unfollow'].count({}))

def append_followers_to_db(users):
	# Add to database
	for i in users:
		db['followers'].update({'_id':i['_id']}, i, True)
	print(db['followers'].count({}))

def append_following_to_db(users):
	# Add to database
	for i in users:
		db['following'].update({'_id':i['_id']}, i, True)
	print(db['following'].count({}))

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
		for follower in followers_list:
			followers.append({
				'username':	follower['screen_name'],
				'_id': follower['id_str']
			})

		cursor = followers_list['next_cursor']

		ctr += 1
		if ctr%15==0:
			print ("Sleeping for 900 seconds")
			time.sleep(900)

	print ("Collected all " + str(len(followers)) + " followers. Storing them in the db")
	append_followers_to_db(followers)

def collect_following_to_unfollow():
	following = list()	
	ctr = 0
	# Store all friends in a db
	while cursor!=0:
		friends_list = twitter.get_friends_list(screen_name=user_to_collect,
													count='200',
													skip_status=True,
													include_user_entities=False,
													cursor=cursor)
		
		for friends in friends_list:
			following.append({
				'username':	follower['screen_name'],
				'_id': follower['id_str']
			})

		cursor = friends_list['next_cursor']

		ctr += 1
		if ctr%15==0:
			print ("Sleeping for 900 seconds")
			time.sleep(900)

	print ("Collected all " + str(len(following)) + " friends. Storing them in the db")
	append_following_to_db(following)

def friends_to_unfollow():
	following = db['following'].find({}, no_cursor_timeout=True)
	followers = db['followers'].find({}, no_cursor_timeout=True)

	unfollow = list()

	month = {'Jan' : 1, 'Feb' : 2, 'Mar' : 3, 'Apr' : 4, 'May' : 5, 'Jun' : 6, 'Jul' : 7, 'Aug' : 8, 'Sep' : 9, 'Oct' : 10, 'Nov' : 11, 'Dec' : 12}
	# To be changed
	last_date = datetime.datetime(2017, 7, 31, 23, 59, 59)

	followers_usernames = []
	for follower in followers:
		followers_usernames.append(follower['username'])

	c = 0
	for friend in following:
		user_name = friend['username']
		# Check if someone we follow don't follow us back
		if user_name in followers_usernames:
 			continue
		else:
			result = client.show_user(screen_name=user_name)

			latest_tweet = result['status']['created_at']
			latest_tweet_dt = datetime.datetime(int(latest_tweet[5]), month[latest_tweet[1]], int(latest_tweet[2]), int(latest_tweet[3][0:2]), int(latest_tweet[3][3:5]), int(latest_tweet[3][6:]))

			num_friends = result['friends_count']
			num_followers = result['followers_count']
			# To be changed
			threshold_for_inout_ratio = 10

			# Check if the last tweet is done before threshold last date
			if latest_tweet_dt < last_date:
				print (username + " added to unfollowing list since his last tweet was done at" + str(latest_tweet_dt))
				
				unfollow.append({
				'username':	friend['username'],
				'_id': friend['_id']
				})

			elif float(num_followers)/num_friends > threshold_for_inout_ratio:
				print (user_name + " added to unfollowing list since his in/out ratio was " +str(float(num_followers)/num_friends))

				unfollow.append({
				'username':	friend['username'],
				'_id': friend['_id']
				})

			c += 1
			if c%900==0:
				print ("Sleeping for 1000 seconds")
				time.sleep(1000)

def unfollow_users():
	users = db['users_to_unfollow'].find({}, no_cursor_timeout=True)
	count = 0
	for user in users:
		try:
			twitter.destroy_friendship(screen_name=user['username'])
			print("Unollowed " + user['username'])
			count += 1
		except Exception as e:
			print("Can't unfollow " + user['username'])
			continue
		else:
			continue
		finally:
			db['users_to_unfollow'].remove({'_id':user['_id']})
			if count%950==0:
				print("Returning...")
				return
			elif count%100==0:
				print("Sleeping 1000 seconds")
				time.sleep(1000)
			elif count%50==0:
				print("Sleeping 500 seconds")
				time.sleep(500)
			elif count%10==0:
				print("Sleeping 250 seconds")
				time.sleep(250)
	users.close()

if __name__ == '__main__':
	try:
		collect_followers()
		print("Sleeping 1000 seconds")
		time.sleep(1000)
		collect_following()
		print("Sleeping 1000 seconds")
		time.sleep(1000)
		friends_to_unfollow()
		print("Sleeping 1000 seconds")
		time.sleep(1000)
		unfollow_users()
	except Exception as e:
		print(e)
		time.sleep(1000)
		unfollow_users()
