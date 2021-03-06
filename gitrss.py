#!/usr/bin/python
import requests
import json
import feedgenerator
import datetime
import dateutil.parser
import sys
import time

# you probably want to change these 2 lines
token = '3e2d13b44b7feb3a5ffd15bc9b981f90e8254314'
baseUrl = 'http://172.18.0.147/api/v3'
msBetweenRequests = 500
daysToPull = 4

def get_forks(repoName):
	return [a['full_name'] for a in json.loads(requests.get('%s/repos/%s/forks?access_token=%s'%(baseUrl,repoName,token)).content)]

def get_branches(repoName):
	resp = json.loads(requests.get('%s/repos/%s/branches?access_token=%s'%(baseUrl, repoName, token)).content)
	return [(a['name'], a['commit']['sha']) for a in resp]

def get_commits(repoName, sha, lastRunDate):
	return [a['sha'] for a in json.loads(requests.get('%s/repos/%s/commits?access_token=%s&sha=%s&since=%s'%(baseUrl, repoName, token, sha, lastRunDate)).content)]


commit_cache = {}
def get_commit(repoName, sha):
	if (repoName + sha) in commit_cache:
		return commit_cache[repoName+sha]
	commit = json.loads(requests.get('%s/repos/%s/commits/%s?access_token=%s'%(baseUrl, repoName, sha, token)).content)
	time.sleep(msBetweenRequests / 1000.0)
	commit_cache[repoName+sha] = commit
	return commit

def remove_dupes(commits):
	shas = set()
	result = []
	commits = sorted(commits, key=lambda a: a['commit']['author']['date'])
	for c in commits:
		sha = c['sha']
		if sha not in shas:
			result.append(c)
			shas.add(sha)
	return result

def format_feed(repoName):
	return dict(
		title=repoName,
		link='http://github.com',
		description = 'Commits to %s' % repoName,
		language='en'
	)

def format_commit(commit):
	files = []
	for f in commit['files']:
		files.append('%s %s (%s)' % (f['status'][0].upper(), f['filename'], f['changes']))
	return dict(
		title=commit['commit']['message'],
		link=commit['url'].replace('api/v3/repos/', '').replace('commits', 'commit'),
		pubdate=dateutil.parser.parse(commit['commit']['author']['date']),
		author_name=commit['commit']['author']['name'],
		author_email=commit['commit']['author']['email'],
		description = '<br/>'.join(files),
		id=commit['sha']
	)

def update_feed(repo, lastUpdated, outPath):
	commits = []
	repos = [repo]
	repos.extend(get_forks(repo))
	for fork in repos:
		print 'trying %s' % fork
		branches = get_branches(fork)
		for branch in branches:
			commitlist = get_commits(fork, branch[1], lastUpdated)
			for c in commitlist:
				commits.append(get_commit(fork, c))
			time.sleep(msBetweenRequests / 1000.0)
	feed = feedgenerator.DefaultFeed(**format_feed(repo))
	commits = [a for a in commits if 'files' in a]
	commits = remove_dupes(commits)
	for commit in commits:
		feed.add_item(**format_commit(commit))
	current = ''
	try:
		current = open(outPath).read()
	except:
		pass
	new = feed.writeString('utf-8')
	if new != current:
		f = open(outPath, 'w')
		f.write(feed.writeString('utf-8'))
	print 'done: %s' % datetime.datetime.now().time()

while True:
	oneweekago = datetime.datetime.now() - datetime.timedelta(daysToPull)
	if len(sys.argv) != 3:
		print 'usage: gitrss repoName outPath'
	else:
		update_feed(sys.argv[-2], oneweekago.isoformat(), sys.argv[-1])
	time.sleep(30)