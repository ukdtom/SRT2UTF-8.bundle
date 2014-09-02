# Convert sidecar subtitle files files into UTF-8 format
# Created by dane22, a Plex community member
#
# Code contributions made by the following:
#	srazer, also a Plex community member
# jmichiel, also a Plex community member
#

# TODO: 
# Check for pref. set language
#

######################################### Global Variables #########################################
PLUGIN_VERSION = '0.0.1.8'

######################################### Imports ##################################################
import os
import shutil
import io
import codecs
import sys
from BeautifulSoup import BeautifulSoup
import fnmatch

import CP_Windows_ISO

import charedSup
from chared import __version__ as VERSION
from chared.detector import list_models, get_model_path, EncodingDetector


######################################## Start of plugin ###########################################
def Start():
	Log.Info(L('Starting') + ' %s ' %(L('Srt2Utf-8')) + L('with a version of') + ' %s' %(PLUGIN_VERSION))
#	print L('Starting') + ' %s ' %(L('Srt2Utf-8')) + L('with a version of') + ' %s' %(PLUGIN_VERSION)
	
####################################### Movies Plug-In #############################################
class srt2utf8AgentMovies(Agent.Movies):
	name = L('Srt2Utf-8') + ' (Movies)'
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
				GetFiles(part)

####################################### TV-Shows Plug-In ###########################################
class srt2utf8AgentTV(Agent.TV_Shows):
	name = L('Srt2Utf-8') + ' (TV)'
	languages = [Locale.Language.NoLanguage]
	primary_provider = False
	contributes_to = ['com.plexapp.agents.thetvdb', 'com.plexapp.agents.none']
	# Return a dummy object to satisfy the framework
	def search(self, results, media, lang):
		results.Append(MetadataSearchResult(id='null', score = 100))
	# Handle the object returned to us, so we can find the directory to look in
	def update(self, metadata, media, lang, force):
		for s in media.seasons:
			if int(s) < 1900:
				for e in media.seasons[s].episodes:
					for i in media.seasons[s].episodes[e].items:
						for part in i.parts:
							GetFiles(part)

######################################### Get files in directory ###################################
def GetFiles(part):
	# Filename of media	
	sFile = part.file.decode('utf-8')
	# Directory where it's located
	sMyDir = os.path.dirname(sFile).decode('utf-8')
	Log.Debug('File trigger is "%s"' %(sFile))
	for root, dirs, files in os.walk(sMyDir, topdown=False):
		# Walk the directory
		for sSrtName in files:
			# Grap all files, and check if it's a valid subtitle file
			sSrtName = sSrtName.decode('utf-8')
			sTest = sIsValid(sMyDir, sFile, sSrtName)
			if sTest != 'null':
				# We got a valid subtitle file here
				if not bIsUTF_8(sTest):
					# Got a language code in the file-name?
					sMyLang = sGetFileLang(sTest)			
					if sMyLang == 'xx':
						sMyLang = GetUsrEncPref()
						sMyLang = Locale.Language.Match(sMyLang)					
					try:
						# Chared supported
						sModel = charedSup.CharedSupported[sMyLang]
						if sModel != 'und':
							Log.Debug('Chared is supported for this language')
							sMyEnc = FindEncChared(sTest, sModel)
					except:
						Log.Debug('Chared is not supported, reverting to Beautifull Soap')
						sMyEnc = FindEncBS(sTest, sMyLang)
					# Convert the darn thing
					if sMyEnc not in ('utf_8', 'utf-8'):
						# Make a backup
						try:
							MakeBackup(sTest)
						except:
							Log.Exception('Something went wrong creating a backup, file will not be converted!!! Check file permissions?')
						else:
							try:
								ConvertFile(sTest, sMyEnc)
							except:
								Log.Exception('Something went wrong converting!!! Check file permissions?')
								try:
									RevertBackup(sTest)
								except:
									Log.Exception("Can't even revert the backup?!? I give up...")
					else:
						Log.Debug('The subtitle file named : %s is already encoded in utf-8, so skipping' %(sTest))
				else:
					Log.Debug('The subtitle file named : %s is already encoded in utf-8, so skipping' %(sTest))

########################################## Convert file to utf-8 ###################################
def ConvertFile(myFile, enc):
	Log.Debug("Converting file: %s with the encoding of %s into utf-8" %(myFile, enc))
	with io.open(myFile, 'r', encoding=enc) as sourceFile, io.open(myFile + '.tmpPlex', 'w', encoding="utf-8") as targetFile:
		targetFile.write(sourceFile.read())
	# Remove the original file
	os.remove(myFile)
	# Name tmp file as the original file name
	os.rename(myFile + '.tmpPlex', myFile)
	Log.Info('Successfully converted %s to utf-8 from %s' %(myFile, enc))

###################### Detect the file encoding using Beautifull Soap #################################
def FindEncBS(myFile, lang):
	try:
		#Read the subtitle file
		Log.Debug('BSFile to encode is %s and filename language is %s' %(myFile, lang))
		f = io.open(myFile, 'rb')
		mySub = f.read()
		soup = BeautifulSoup(mySub)
		soup.contents[0]
		f.close()
		sCurrentEnc = soup.originalEncoding
		Log.Debug('BeautifulSoup reports encoding as %s' %(sCurrentEnc))
		if sCurrentEnc == 'ascii':
			return 'utf-8'
		if sCurrentEnc != 'utf-8':
			# Check result from BeautifulSoup against languagecode from filename
			if lang != 'und':
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

		return sCurrentEnc
	except UnicodeDecodeError:
		Log.Debug('got unicode error with %s' %(myFile))
		RevertBackup(myFile)
		return False

######################################### Detect the file encoding with chared #####################
def FindEncChared(sMyFile, sModel):
	try:
		# get model file
		model_file = get_model_path(sModel)
		if os.path.isfile(model_file):
			# load model file
			encoding_detector = EncodingDetector.load(model_file)
			# load subtitle
			fp = io.open(sMyFile, 'rb')
			document = fp.read()
			# find codepage
			clas = encoding_detector.classify(document)
			myEnc = clas[0]
			Log.Debug('%s Chared encoding detected as %s' %(sMyFile, myEnc))
			return myEnc
		else:
			Log.Debug('No Language module for %s' %(model_file))
			return 'und'
	except:
		Log.Critical("Unable to load charset detection model from %s. Not supported." %(sModel))

#################### If no language was detected, we need to grap any User Prefs ##############################
def GetUsrEncPref():
	return Prefs['PreferredCP']

#################### Grap a language code from the filename, if present ##############################
# If a language code is present in the filename, then this function will return it
# If no language code is present, it'll return 'xx'
def sGetFileLang(sMyFile):
	# Get the filename
	sFileName, sFileExtension = os.path.splitext(sMyFile)
	# Get language code if present, or else return 'xx'
	sFileName, sFileExtension = os.path.splitext(sFileName)
	myLang = sFileExtension[1:].lower()
	return Locale.Language.Match(myLang)

############################## Returns true is file is in utf-8 #####################################
# Check if the subtitle file already is in utf-8, and if so, returns true
def bIsUTF_8(sMyFile):
	try:
		#Read the subtitle file
		f = io.open(sMyFile, 'rb')
		mySub = f.read()
		soup = BeautifulSoup(mySub)
		soup.contents[0]
		f.close()
		sCurrentEnc = soup.originalEncoding
		if sCurrentEnc == 'utf-8':
			return True
		else:
			return False
	except:
		return False

######################################### Is file valid? ############################################
# Returns a filename of a valid subtitle file, or 'null' if it's a no-go
def sIsValid(sMyDir, sMediaFilename, sSubtitleFilename):
	try:
		Log.Debug('Checking if file %s is valid' %(sSubtitleFilename))
		# Valid list of subtitle ext.	
		lValidList = Prefs['Valid_Ext'].upper().split()
		# Get the ext of the SubtitleFile
		sFileName, sFileExtension = os.path.splitext(sSubtitleFilename)
		# Is this a valid subtitle file?
		if (sFileExtension.upper() in lValidList):
			#It's a subtitle file, but is it for the mediafile?
			# Get filename without ext. of the media
			myMedia, myMediaExt = os.path.splitext(os.path.basename(sMediaFilename))
			# Get the ext of the SubtitleFile
			sSRTName2, sFileExtension = os.path.splitext(sFileName)
			if sFileName == myMedia:
				Log.Debug('Found a valid subtitle file named "%s"' %(sSubtitleFilename))
				sSource = sMyDir + '/' + sSubtitleFilename
				return sSource
			elif myMedia == sSRTName2:
				Log.Debug('Found a valid subtitle file named "%s"' %(sSubtitleFilename))
				sSource = sMyDir + '/' + sSubtitleFilename
				return sSource
			else:
				return 'null'
		else:
			return 'null'
	except:
		Log.Exception('An exception happened in function sIsValid in dir %s for media %s and file %s' %(sMyDir, sMediaFilename, sSubtitleFilename))
		return 'null'

######################################## Make the backup, if enabled ###############################
def MakeBackup(file):
	if Prefs['Make_Backup']:
		iCounter = 1
		sTarget = file + '.' + 'Srt2Utf-8'
		# Make sure we don't override an already existing backup
		while os.path.isfile(sTarget):
			sTarget = file + '.' + str(iCounter) + '.Srt2Utf-8'
			iCounter = iCounter + 1
		Log.Debug('Making a backup of %s as %s' %(file, sTarget))
		shutil.copyfile(file, sTarget)

######################################## Dummy to avoid bad logging ################################
def ValidatePrefs():
	print Prefs['PreferredCP'] + ': ' + Locale.Language.Match(Prefs['PreferredCP'])
	return

######################################## Revert the backup, if enabled #############################
def RevertBackup(file):
	if Prefs['Make_Backup']:
		Log.Critical('**** Reverting from backup, something went wrong here ****')	
		# Look back of a maximum of 250 backup's
		iCounter = 250
		sTarget = file + '.' + str(iCounter) + '.' + 'Srt2Utf-8'
		# Make sure we don't override an already existing backup
		while not os.path.isfile(sTarget):
			if iCounter == 0:
				sTarget = file + '.' + 'Srt2Utf-8'
			else:				
				sTarget = file + '.' + str(iCounter) + '.' + 'Srt2Utf-8'
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

