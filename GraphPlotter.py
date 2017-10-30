import tweepy, json, sys, string, csv
from pymongo import MongoClient
import matplotlib.pyplot as plt
from environment import api_key, user_to_collect

def plotLine(keys, values, x, xlabel, ylabel, title, filename, rotation = 0):
	plt.figure(figsize = (8,8))
	plt.xticks(x, keys, rotation = rotation)
	plt.xlabel(xlabel)
	plt.ylabel(ylabel)
	plt.plot(x ,values)
	plt.title(title)
	plt.savefig("graphs/" + filename)

# CONSUMER_KEY = 'EIDeo5t9tyKO01Cs4xV0bdvnR'
# CONSUMER_SECRET =  'rUKtUAaYtTH1iCgfqJenglLk3gg1rHjb2k1jMZXr6XL6SIUzwU'
# ACCESS_TOKEN = '1544789976-GPkfyjaeNh9G1i4hZX70KLOmZpkfwGNCsd8ty3V'
# ACCESS_SECRET	= 'b8zJPp6eQkq1oaJyb60cdb1Hx5H88vk0ifSifEZkwn4uY'

auth = tweepy.OAuthHandler(api_key['api_key'], api_key['api_secret'])
auth.set_access_token(api_key['access_token'], api_key['access_token_secret'])
api = tweepy.API(auth, wait_on_rate_limit = True, wait_on_rate_limit_notify = True)

if (not api):
	print ('Problem Connecting to API')
	sys.exit(-1)

usr = user_to_collect

followers = []
for page in tweepy.Cursor(api.followers, screen_name=usr).pages():
	for user in page:
		print("Follower - " + user.screen_name)
		followers.append(user.screen_name)

following = []
for page in tweepy.Cursor(api.friends, screen_name=usr).pages():
	for user in page:
                print("Following - " + user.screen_name)
		following.append(user.screen_name)

u = [usr]
nodes = set(followers + following + u)
print(len(nodes))

with open('graphs/nodes.csv', 'w') as csvfile:
    fieldnames = ['id', 'label']
    writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
    writer.writeheader()
    i = 1
    for n in nodes:
    	writer.writerow({'id' : i, 'label': n})
    	i += 1

with open('graphs/edges.csv', 'w') as csvfile:
	fieldnames = ['source', 'target']
	writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
	writer.writeheader()
	for n in range(len(followers)):
		writer.writerow({'source' : followers[n], 'target': usr})
	for n in range(len(following)):
		writer.writerow({'source' : usr, 'target': following[n]})

last_id = None
rt_count = 0
fv_count = 0
tweets = api.user_timeline(screen_name = usr, count=200, max_id = last_id)
while tweets:
	for tweet in tweets:
		if not tweet.retweeted:
			rt_count += tweet.retweet_count
		fv_count += tweet.favorite_count
	last_id = tweets[len(tweets)-1].id - 1
	print("Last ID - " + last_id)
	tweets = api.user_timeline(screen_name = usr, count=200, max_id = last_id)

client = MongoClient()
db = client['FriendsFarmer']
graph_data_db = db['graph']

g_data = {}
g_data['num_followers'] = len(followers)
g_data['num_following'] = len(following)
g_data['indeg_outdeg_ratio'] = float(len(followers))/len(following)
g_data['rt_count'] = rt_count
g_data['fv_count'] = fv_count
graph_data_db.insert(json.loads(json.dumps(g_data)))


num_followers = []
num_following = []
indeg_outdeg_ratio = []
rt_count = []
fv_count = []
day = []
graph_cursor = graph_data_db.find({})

i = 1
for d in graph_cursor:
	num_followers.append(d['num_followers'])
	num_following.append(d['num_following'])
	indeg_outdeg_ratio.append(d['indeg_outdeg_ratio'])
	rt_count.append(d['rt_count'])
	fv_count.append(d['fv_count'])
	day.append(i)
	i += 1

plotLine(day, num_followers, day, 'Days elapsed', 'Number of followers', 'Followers', 'Followers')
plotLine(day, num_following, day, 'Days elapsed', 'Number of following', 'Following', 'Following')
plotLine(day, indeg_outdeg_ratio, day, 'Days elapsed', 'Indegree/Outdegree ratio', 'In/Out', 'In_Out')
plotLine(day, rt_count, day, 'Days elapsed', 'Number of RTs on all tweets', 'Number of RTs', 'RTs')
plotLine(day, fv_count, day, 'Days elapsed', 'Number of favorites', 'No of fv', 'fvs')
