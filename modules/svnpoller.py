#!/usr/bin/env python
'''A Phenny extension that polls SVN repos'''

import re
import os
from subprocess import Popen, PIPE
import xml.etree.ElementTree as ET
from io import StringIO
import time
from tools import db_path, generate_report, truncate

global_revisions = None
global_filename = None

def loadRevisions(fn): 
	result = {}
	with open(fn) as f:
		for line in f: 
			line = line.strip()
			if line: 
				try: repo, rev = line.split('\t', 2)
				except ValueError: continue # @@ hmm
				result.setdefault(repo, int(rev)) #[]).append((teller, verb, timenow, msg))
	return result

def dumpRevisions(fn, data): 
	with open(fn, 'w') as f:
		for repo in data.keys():
			line = '\t'.join((repo, str(data[repo])))
			try: f.write(line + '\n')
			except IOError: break
	return True

def setup(self):
	global global_revisions, global_filename
	global_filename = db_path(self, 'repos')
	if not os.path.exists(global_filename): 
		try: f = open(global_filename, 'w')
		except OSError: pass
		else: 
			f.write('')
			f.close()
	global_revisions = loadRevisions(global_filename) # @@ tell
	#self.say(str(global_revisions))
	

class SVNPoller:
	def __init__(self, repo, root):
		self.pre = ["svn", "--xml"]
		self.root = root
		self.repo = repo
		self.last_revision = None
		self.latest_revision = None

	def __str__(self):
		return "(%s) %s %s" % (self.repo, self.root, self.last_revision)

	def check(self, revisions):
		global global_revisions
		if self.repo not in revisions:
			revisions[self.repo] = 0
		self.last_revision = global_revisions[self.repo]
		self.latest_revision = self.get_last_revision()
		print(str(self.latest_revision), str(self.last_revision), str(global_revisions))
		## if successfully polled and a new revision ##
		if self.latest_revision > self.last_revision:
			for msg in self.newReport(self.latest_revision):
				yield (msg, global_revisions)

	def newReport(self, something_else):
		if self.last_revision == 0 or self.last_revision == None:
			self.last_revision = self.latest_revision - 1
		for rev in range(self.last_revision+1, self.latest_revision+1):
			msg = self.generateReport(rev)
			#if not msg:
			#	msg = ":("
			#yield msg
			if msg:
				yield msg


	def svn(self, *cmd):
		command = " ".join(self.pre)
		command = command + " " + " ".join(list(cmd))
		command = command + " " + " ".join([self.root])
		pipe = Popen(command.split(" "), stdout=PIPE)
		try:
			data = pipe.communicate()[0]
		except IOError:
			data = ""
		return ET.fromstring(data.decode())


	def get_last_revision(self):
		global global_revisions
		tree = self.svn("info")
		revision = tree.find("entry").find("commit").get("revision")
		global_revisions[self.repo] = int(revision)
		return int(revision)


	def revision_info(self, revision):
		tree = self.svn("log", "-r", str(revision), "--verbose")
		treeAuthor = tree.find(".//author")
		if treeAuthor is not None:
			author = treeAuthor.text
		else: author = "no author"
		treeComment = tree.find(".//msg")
		if treeComment is not None:
			comment = treeComment.text
		else: comment = "no comment"
		#self.say(author, "∞", comment)
		modified_paths = []
		added_paths = []
		removed_paths = []
		for path in tree.findall(".//path"):
			if path.get('action') == "A":
				added_paths.append(path.text)
			elif path.get('action') == "D":
				removed_paths.append(path.text)
			else:
				modified_paths.append(path.text)
		treeDate = tree.find(".//date")
		if treeDate is not None:
			date = time.strptime(tree.find(".//date").text, "%Y-%m-%dT%H:%M:%S.%fZ")
			date = time.strftime("%d %b %Y %H:%M:%S", date)
		else:
			date = "no date"
		return self.repo, author, comment, modified_paths, added_paths, removed_paths, date, str(revision)


	def generateReport(self, rev, showDate=False):
		repo, author, comment, modified_paths, added_paths, removed_paths, date, rev = self.revision_info(rev)
		if showDate == True:
			msg = generate_report(repo, author, comment, modified_paths, added_paths, removed_paths, rev, date)
		else:
			msg = generate_report(repo, author, comment, modified_paths, added_paths, removed_paths, rev, "")
		return msg

	def sourceforgeURL(self, rev):
	    if self.root.endswith('svn'):
		    return 'https://sourceforge.net/p/' + self.repo + '/svn/%s' % str(rev)
	    else:
		    return 'https://sourceforge.net/p/' + self.repo + '/code/%s' % str(rev)

def recentcommits(phenny, input):
	"""List the most recent SVN commits."""
	print("POLLING!!!!")
	if phenny.config.svn_repositories is None:
		phenny.say("SVN module cannot function without repositories being set in the config file!")
		return
	for repo in phenny.config.svn_repositories:
		#phenny.say("{}: {}".format(repo, phenny.config.svn_repositories[repo]))
		poller = SVNPoller(repo, phenny.config.svn_repositories[repo])
		#for (msg, revisions) in pollers[repo].check(phenny.revisions):
		rev = poller.get_last_revision()
		msg = poller.generateReport(rev, True)
		url = poller.sourceforgeURL(rev)
		phenny.say(truncate(msg, '{} ' + url))
recentcommits.name = 'recent'
recentcommits.rule = ('$nick', 'recent')
recentcommits.example = 'begiak: recent'
#recentcommits.event = "PING"
#recentcommits.rule = r'.*'
recentcommits.priority = 'medium'
recentcommits.thread = True

def retrieve_commit_svn(phenny, input):
	data = input.group(1).split(' ')
	
	if len(data) != 2:
		phenny.reply("Invalid number of parameters.")
		return
		
	repo = data[0]
	rev = data[1]
	
	if repo in phenny.config.git_repositories:
		return
	
	if repo not in phenny.config.svn_repositories:
		phenny.reply("That repository is not monitored by me!")
		return
	
	poller = SVNPoller(repo, phenny.config.svn_repositories[repo])
	msg = poller.generateReport(rev, True)
	url = poller.sourceforgeURL(rev)
	phenny.say(truncate(msg, '{} ' + url))
retrieve_commit_svn.rule = ('$nick', 'info(?: +(.*))')

def pollsvn(phenny, input):
	global global_revisions, global_filename
	results = False
	#phenny.say("POLLING!!!!")
	print("POLLING!!!!")
	if phenny.config.svn_repositories is None:
		phenny.say("SVN module cannot function without repositories being set in the config file!")
		return
	pollers = {}
	#phenny.say("OLD REVISION NUMBERS: " + str(global_revisions))
	for repo in phenny.config.svn_repositories:
		pollers[repo] = SVNPoller(repo, phenny.config.svn_repositories[repo])
	for repo in phenny.config.svn_repositories:
		#phenny.say(str(pollers[repo]))
		allRevs = []
		for (msg, revisions) in pollers[repo].check(global_revisions):
			x = (msg,revisions)
			allRevs.append(x)
			#print("x: ", x)
		#print("a: ", allRevs)
		if len(allRevs) > 3:
			toReport = [allRevs[0], ("...", {}), allRevs[-1]]
		else:
			toReport = allRevs
		print('t: ', toReport)
		for (msg, revisions) in toReport:
			#phenny.say("NEW REVISION NUMBERS: " + str(global_revisions))
			if msg is not None:
				results = True
				print("msg: %s" % msg)
				if hasattr(phenny.config, 'svn_channels'):
					if repo in phenny.config.svn_channels:
						for chan in phenny.config.svn_channels[repo]:
							print("chan, msg: %s, %s" % (chan, msg))
							phenny.msg(chan, msg)
				else:
					for chan in phenny.config.channels:
						print("chan, msg: %s, %s" % (chan, msg))
						phenny.msg(chan, msg)
			if global_revisions:
				if len(global_revisions) > 0:
					print("dumping revisions")
					dumpRevisions(global_filename, global_revisions)
	#phenny.say("done")
	print("POLLED")
	return results
pollsvn.name = 'SVN poll'
pollsvn.event = "PONG"
pollsvn.rule = r'.*'
pollsvn.priority = 'medium'

def esan(phenny, input):
	phenny.reply("Hold on a second, I'm polling!")
	results = pollsvn(phenny, input)
	if results == False:
		phenny.reply("Sorry, there was nothing to report.")
esan.rule = ('$nick', 'esan!')
