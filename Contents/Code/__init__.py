# Convert sidecar subtitle files files into UTF-8 format
# Created by dane22, a Plex community member
#
# Code contributions made by srazer, also a Plex community member
#

# TODO: 
# Check for pref. set language
#

######################################### Global Variables #########################################
sVersion = '0.0.1.3'
sTitle = 'SRT2UTF-8'

######################################### Imports ##################################################
import os
import shutil
import io
import codecs
import sys
from BeautifulSoup import BeautifulSoup
import fnmatch
import CP_Windows_ISO
import langCodeTwo
import langCodeTree

######################################## Start of plugin ###########################################
def Start():
	Log.Info('Starting %s with a version of %s' %(sTitle, sVersion))
	print 'Starting %s with a version of %s' %(sTitle, sVersion)

####################################### Movies Plug-In #############################################
class srt2utf8AgentMovies(Agent.Movies):
	name = sTitle + ' (Movies)'
	languages = [Locale.Language.NoLanguage]
	primary_provider = False
	contributes_to = ['com.plexapp.agents.imdb', 'com.plexapp.agents.themoviedb', 'com.plexapp.agents.none']
	# Return a dummy object to satisfy the framework
	def search(self, results, media, lang, manual):
		results.Append(MetadataSearchResult(id='null', score = 100))
    	# Handle the object returned to us, so we can find the directory to look in
	def update(self, metadata, media, lang, force):
		for i in media.items:
			for part in i.parts:
				FindSRT(part)

####################################### TV-Shows Plug-In ###########################################
class srt2utf8AgentTV(Agent.TV_Shows):
	name = sTitle + ' (TV)'
	languages = [Locale.Language.NoLanguage]
	primary_provider = False
	contributes_to = ['com.plexapp.agents.thetvdb', 'com.plexapp.agents.none']
	def search(self, results, media, lang):
		results.Append(MetadataSearchResult(id='null', score = 100))
	# Handle the object returned to us, so we can find the directory to look in
	def update(self, metadata, media, lang, force):
		for s in media.seasons:
			if int(s) < 1900:
				for e in media.seasons[s].episodes:
					for i in media.seasons[s].episodes[e].items:
						for part in i.parts:
							FindSRT(part)

######################################### Find valid sidecars ######################################
def FindSRT(part):
	# Filename of media	
	file = part.file.decode('utf-8')
	# Directory where it's located
	myDir = os.path.dirname(file)
	# Valid list of subtitle ext.	
	lValidList = Prefs['Valid_Ext'].upper().split()
	# Get filename without ext. of the media
	myMedia, myMediaExt = os.path.splitext(os.path.basename(file))
	Log.Debug('File trigger is "%s"' %(file))
	Log.Debug('Searching directory: %s' %(myDir))
	for root, dirs, files in os.walk(myDir, topdown=False):
		for name in files:
			Log.Debug('In Dir %s %s found a file named: "%s"' %(myDir, sTitle, name))
			# Get the ext
			sFileName, sFileExtension = os.path.splitext(name)
			# Is this a valid subtitle file?
			if (sFileExtension.upper() in lValidList):
				if fnmatch.fnmatch(name, myMedia + '*'):
					Log.Debug('Found a valid subtitle file named "%s"' %(name))
					sSource = myDir + '/' + name
					GetEnc(sSource, FindLanguage(sSource))

######################################### Find language in filename #################################
def FindLanguage(srtFile):
	# Get the filename
	sFileName, sFileExtension = os.path.splitext(srtFile)
	# Get language code if present, or else return 'und'
	sFileName, sFileExtension = os.path.splitext(sFileName)
	myLang = sFileExtension[1:].lower()
	if (myLang in langCodeTwo.langCodeTwo):
		return myLang
	elif (myLang in langCodeTree.langCodeTree):
		return myLang
	else:
		return 'und'

######################################### Detect the file encoding #################################
def GetEnc(myFile, lang):
	try:
		#Read the subtitle file
		Log.Debug('File to encode is %s and filename language is %s' %(myFile, lang))
		f = io.open(myFile, 'rb')
		mySub = f.read()
		soup = BeautifulSoup(mySub)
		soup.contents[0]
		f.close()
		sCurrentEnc = soup.originalEncoding
		Log.Debug('BeautifulSoup reports encoding as %s' %(sCurrentEnc))
		if sCurrentEnc != 'utf-8':
			# Not utf-8, so let's make a backup
			MakeBackup(myFile)
			# Check result from BeautifulSoup against languagecode from filename
			if lang != 'und':
				print 'Checking Language against BS ' + myFile
				# Was it a windows codepage?
				if 'windows-' in sCurrentEnc:
					# Does result so far match our list?
					if sCurrentEnc == CP_Windows_ISO.cpWindows[lang]:
						Log.Debug('Origen CP is %s' %(sCurrentEnc))
					else:
						if CP_Windows_ISO.cpWindows[lang] != "Unknown":
							sCurrentEnc = CP_Windows_ISO.cpWindows[lang]
							Log.Debug('Overriding detection due to languagecode in filename, and setting encoding to %s' %(sCurrentEnc))
						else:
							Log.Debug('******* SNIFF *******')
							Log.Debug("We don't know the default encodings for %s" %(lang))
							Log.Debug('If you know this, then please go here: https://forums.plex.tv/index.php/topic/94864-rel-str2utf-8/ and tell me')

				else:
					# We got ISO
					# Does result so far match our list?
					if sCurrentEnc == CP_Windows_ISO.cpISO[lang]:
						Log.Debug('Origen CP is %s' %(sCurrentEnc))
					else:
						if CP_Windows_ISO.cpWindows[lang] != "Unknown":
							sCurrentEnc = CP_Windows_ISO.cpISO[lang]
							Log.Debug('Overriding detection due to languagecode in filename, and setting encoding to %s' %(sCurrentEnc))
						else:
							Log.Debug('******* SNIFF *******')
							Log.Debug("We don't know the default encodings for %s" %(lang))
							Log.Debug('If you know this, then please go here: https://forums.plex.tv/index.php/topic/94864-rel-str2utf-8/ and tell me')

			ConvertFile(myFile, sCurrentEnc)
		return (soup.originalEncoding == 'utf-8')
	except UnicodeDecodeError:
		Log.Debug('got unicode error with %s' %(myFile))
		RevertBackup(myFile)
		return False

######################################## Revert the backup, if enabled #############################
def RevertBackup(file):
	if Prefs['Make_Backup']:
		Log.Critical('**** Reverting from backup, something went wrong here ****')	
		# Look back of a maximum of 250 backup's
		iCounter = 250
		sTarget = file + '.' + str(iCounter) + '.' + sTitle
		# Make sure we don't override an already existing backup
		while not os.path.isfile(sTarget):
			if iCounter == 0:
				sTarget = file + '.' + sTitle
			else:				
				sTarget = file + '.' + str(iCounter) + '.' + sTitle
			iCounter = iCounter -1
		Log.Debug('Reverting from backup of %s' %(sTarget))
		shutil.copyfile(sTarget, file)
		# Cleanup bad tmp file
		if os.path.isfile(file + '.tmpPlex'):
			os.remove(file + '.tmpPlex')
		# Remove unneeded backup
		if os.path.isfile(sTarget):
			os.remove(sTarget)
		
	else:
		Log.Critical('**** Something went wrong here, but backup has been disabled....SIGH.....Your fault, not mine!!!!! ****')			

######################################## Make the backup, if enabled ###############################
def MakeBackup(file):
	if Prefs['Make_Backup']:	
		iCounter = 1
		sTarget = file + '.' + sTitle
		# Make sure we don't override an already existing backup
		while os.path.isfile(sTarget):
			sTarget = file + '.' + str(iCounter) + '.' + sTitle
			iCounter += iCounter
		Log.Debug('Making a backup of %s' %(file))
		shutil.copyfile(file, sTarget)

######################################## Dummy to avoid bad logging ################################
def ValidatePrefs():
	return

########################################## Convert file to utf-8 ###################################
def ConvertFile(myFile, enc):
	Log.Debug('Converting file %s with an encoding of %s' %(myFile, enc))
	sourceFile = io.open(myFile, 'r', encoding=enc)
	targetFile = io.open(myFile + '.tmpPlex', 'w', encoding="utf-8")
	while True:
		contents = sourceFile.read()
		if not contents:
			break
		targetFile.write(contents)
	sourceFile.close()
	targetFile.close()
	# Remove the original file
	os.remove(myFile)
	# Name tmp file as the original file name
	os.rename(myFile + '.tmpPlex', myFile)
	Log.Info('Successfully converted %s to utf-8' %(myFile))
