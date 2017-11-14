import json
import time
from twython import Twython
from pymongo import MongoClient
from environment import api_key, user_to_collect
import matplotlib.pyplot as plt

connection = MongoClient()
db = connection['FriendsFarmer']
cdf_graph = db['cdf_graph']

# Creating the Twython object
twitter = Twython(
	api_key['api_key'],
	api_key['api_secret'],
	api_key['access_token'],
	api_key['access_token_secret']
)

def collect_data():
	cursor = -1
	ctr = 0
	# Collect current user's followers
	while cursor!=0:
		followers_list = twitter.get_followers_list(screen_name=user_to_collect,
													count='200',
													skip_status=True,
													include_user_entities=True,
													cursor=cursor)
		ctr += 1

		if ctr%15 == 0:
			print ('Sleeping for 1000 seconds')
			time.sleep(1000)

		cursor = followers_list['next_cursor']

		for follower in followers_list['users']:
			num_friends = follower['friends_count']
			num_followers = follower['followers_count']
			user_name = follower['screen_name']
			# print(str(user_name) + ' has ' + str(num_followers) + ' Followers and follows ' + str(num_friends))

			follower_data = {'screen_name': user_name, 'num_followers': num_followers,
							'num_following': num_friends,
							'indeg_outdeg_ratio': float(num_followers)/(num_friends)}

			cdf_graph.insert(json.loads(json.dumps(follower_data)))

def make_cdf():
	graph_cursor = cdf_graph.find({})

	in_out = []
	for follower in graph_cursor:
		print (follower['screen_name'] + ' ' + str(follower['indeg_outdeg_ratio']) + ' ' + str(follower['num_followers']) + ' ' + str(follower['num_following']))
		in_out.append(follower['indeg_outdeg_ratio'])

	plt.hist(sorted(in_out), normed=True, cumulative=True, label='CDF', histtype='step', alpha=0.8, color='k')
	plt.xlabel('In/Out')
	plt.ylabel('CDF of Followers')

	plt.savefig('graphs/CDFGraph')

if __name__ == '__main__':
	collect_data()
	make_cdf()
