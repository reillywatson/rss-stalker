#!/usr/bin/python
import requests
import json
import feedgenerator
import datetime
import dateutil.parser
import sys

# you probably want to change these 2 lines
token = '3e2d13b44b7feb3a5ffd15bc9b981f90e8254314'
baseUrl = 'http://172.18.0.147/api/v3'

def get_forks(repoName):
	return [a['full_name'] for a in json.loads(requests.get('%s/repos/%s/forks?access_token=%s'%(baseUrl,repoName,token)).content)]

def get_branches(repoName):
	resp = json.loads(requests.get('%s/repos/%s/branches?access_token=%s'%(baseUrl, repoName, token)).content)
	return [(a['name'], a['commit']['sha']) for a in resp]

def get_commits(repoName, sha, lastRunDate):
	return [a['sha'] for a in json.loads(requests.get('%s/repos/%s/commits?access_token=%s&sha=%s&since=%s'%(baseUrl, repoName, token, sha, lastRunDate)).content)]

def get_commit(repoName, sha):
	return json.loads(requests.get('%s/repos/%s/commits/%s?access_token=%s'%(baseUrl, repoName, sha, token)).content)

def remove_dupes(commits):
	shas = set()
	result = []
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
		files.append('%s %s' % (f['status'], f['filename']))
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
	feed = feedgenerator.DefaultFeed(**format_feed(repo))
	commits = [a for a in commits if 'files' in a]
	commits = remove_dupes(commits)
	for commit in commits:
		feed.add_item(**format_commit(commit))
	f = open(outPath, 'w')
	f.write(feed.writeString('utf-8'))

oneweekago = datetime.datetime.now() - datetime.timedelta(7)
if len(sys.argv) != 3:
	print 'usage: gitrss repoName outPath'
else:
	update_feed(sys.argv[-2], oneweekago.isoformat(), sys.argv[-1])
