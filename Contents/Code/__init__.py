# Convert sidecar subtitle files files into UTF-8 format
# Created by dane22, a Plex community member
#
# Code contributions made by the following:
# srazer, also a Plex community member
# jmichiel, also a Plex community member
#

# TODO:
# Check for pref. set language
#

# ############################ Imports ############################

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


# ############################ Global Variables ###################
PLUGIN_VERSION = '0.0.2.5'


def Start():
    """ Start of plugin """
    strLog = ''.join((
        str(L('Starting')),
        ' %s ' % (L('Srt2Utf-8')),
        str(L('with a version of')),
        str(' %s on %s' % (PLUGIN_VERSION, Platform.OS))))
    Log.Info(strLog)
    try:
        print strLog
    except Exception:
        pass


class srt2utf8AgentMovies(Agent.Movies):
    """ Movies Plug-In """
    name = L('Srt2Utf-8') + ' (Movies)'
    languages = [Locale.Language.NoLanguage]
    primary_provider = False
    contributes_to = [
        'com.plexapp.agents.imdb',
        'com.plexapp.agents.themoviedb',
        'com.plexapp.agents.none']

    def search(self, results, media, lang, manual):
        """ Return a dummy object to satisfy the framework """
        results.Append(MetadataSearchResult(id='null', score=100))

    def update(self, metadata, media, lang, force):
        """ Handle the object returned to us, so we
        can find the directory to look in """
        for i in media.items:
            for part in i.parts:
                # Get OpenSubtitles SRT's
                GetOSSrt(part)
                # Get SideCars
                GetFiles(part)


class srt2utf8AgentTV(Agent.TV_Shows):
    """ TV-Shows Plug-In """
    name = L('Srt2Utf-8') + ' (TV)'
    languages = [Locale.Language.NoLanguage]
    primary_provider = False
    contributes_to = [
        'com.plexapp.agents.thetvdb',
        'com.plexapp.agents.themoviedb']

    # Return a dummy object to satisfy the framework
    def search(self, results, media, lang):
        results.Append(MetadataSearchResult(id='null', score=100))

    # Handle the object returned to us, so we can find the directory to look in
    def update(self, metadata, media, lang, force):
        for s in media.seasons:
            if int(s) < 1900:
                for e in media.seasons[s].episodes:
                    for i in media.seasons[s].episodes[e].items:
                        for part in i.parts:
                            GetOSSrt(part)
                            GetFiles(part)


def GetOSSrt(part):
    """ Scan for OS srt's """
    if Prefs['OSEnabled']:
        sHash = part.hash
        Log.Debug('Part Hash is %s' % (sHash))
        # Get path to this parts OS-Srt's
        OSDir = os.path.join(
            Core.app_support_path,
            'Media',
            'localhost',
            sHash[0],
            sHash[1:] + '.bundle',
            'Contents',
            'Subtitle Contributions',
            'com.plexapp.agents.opensubtitles')
        for root, dirs, files in os.walk(OSDir, topdown=True):
            for langCode in dirs:
                for root2, dirs2, files2 in os.walk(
                    os.path.join(
                        OSDir,
                        langCode),
                        topdown=False):
                    # Walk the directory
                    for sSrtName in files2:
                        sMySrtFile = os.path.join(
                            OSDir,
                            langCode,
                            sSrtName)
                        # Get the ext of the SubtitleFile
                        sFileName, sFileExtension = os.path.splitext(sSrtName)
                        # Is this a backup file?
                        if sFileExtension != '.Srt2Utf-8':
                            # Nope, so go ahead
                            Log.Debug('Checking file: %s' % (sMySrtFile))
                            if not bIsUTF_8(sMySrtFile):
                                strLogEntry = ''.join((
                                    '****** File is not UTF-8',
                                    '...Need to fix it *******'
                                ))
                                Log.Debug(strLogEntry)
                                FixFile(sMySrtFile, langCode)
                            else:
                                Log.Debug('File is okay')


def FixFile(sFile, sMyLang):
    """ Fix the file """
    try:
        # Chared supported
        sModel = charedSup.CharedSupported[sMyLang]
        if sModel != 'und':
            Log.Debug('Chared is supported for this language')
            sMyEnc = FindEncChared(sFile, sModel)
    except:
        Log.Debug('Chared is not supported, reverting to Beautifull Soap')
        sMyEnc = FindEncBS(sFile, sMyLang)
    # Convert the darn thing
    if sMyEnc not in ('utf_8', 'utf-8'):
        # Make a backup
        try:
            MakeBackup(sFile)
        except Exception, e:
            strLog = ''.join((
                'Something went wrong creating a backup, ',
                'file will not be converted!!! ',
                '%s' % str(e)
            ))
            Log.Exception(strLog)
        else:
            try:
                ConvertFile(sFile, sMyEnc)
            except Exception, e:
                Log.Exception('Something went wrong converting!!! %s' % str(e))
                try:
                    RevertBackup(sFile)
                except:
                    Log.Exception("Can't even revert the backup?!? I give up.")
    else:
        strLogEnty = ''.join((
            'The subtitle file named : ',
            '%s' % (sFile),
            'is already encoded in utf-8, so skipping'
        ))
        Log.Debug(strLogEnty)


def GetFiles(part):
    """ Get files in directory """
    # Filename of media
    sFile = part.file.decode('utf-8')
    # Directory where it's located
    sMyDir = os.path.dirname(sFile).decode('utf-8')
    Log.Debug('SideCar File trigger is "%s"' % (sFile))
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
                    FixFile(sTest, sMyLang)
                else:
                    strLog = ''.join((
                        'The subtitle file named : ',
                        '%s' % (sTest),
                        ' is already encoded in utf-8, so skipping'
                    ))
                    Log.Debug(strLog)


def ConvertFile(myFile, enc):
    """ Convert file to utf-8 """
    Log.Debug(
        "Converting file: %s with the encoding of %s into utf-8" % (
            myFile, enc))
    with io.open(
        myFile,
        'r',
        encoding=enc) as sourceFile, io.open(
            myFile + '.tmpPlex',
            'w',
            encoding="utf-8") as targetFile:
        targetFile.write(sourceFile.read())
    # Remove the original file
    os.remove(myFile)
    # Name tmp file as the original file name
    os.rename(myFile + '.tmpPlex', myFile)
    Log.Info('Successfully converted %s to utf-8 from %s' % (myFile, enc))


def FindEncBS(myFile, lang):
    """ Detect the file encoding using Beautifull Soap """
    try:
        # Read the subtitle file
        strLog = ''.join((
            'BSFile to encode is ',
            '%s ' % myFile,
            'and filename language is ',
            '%s' % lang
        ))
        Log.Debug(strLog)
        f = io.open(myFile, 'rb')
        mySub = f.read()
        soup = BeautifulSoup(mySub)
        soup.contents[0]
        f.close()
        sCurrentEnc = soup.originalEncoding
        Log.Debug('BeautifulSoup reports encoding as %s' % (sCurrentEnc))
        if sCurrentEnc == 'ascii':
            return 'utf-8'
        if sCurrentEnc != 'utf-8':
            # Check result from BeautifulSoup against
            # languagecode from filename
            if lang != 'und':
                # Was it a windows codepage?
                if 'windows-' in sCurrentEnc:
                    # Does result so far match our list?
                    if sCurrentEnc == CP_Windows_ISO.cpWindows[lang]:
                        Log.Debug('Origen CP is %s' % (sCurrentEnc))
                    else:
                        if CP_Windows_ISO.cpWindows[lang] != "Unknown":
                            sCurrentEnc = CP_Windows_ISO.cpWindows[lang]
                            strLog = ''.join((
                                'Overriding detection due to languagecode in',
                                ' filename, and setting encoding to ',
                                '%s' % (sCurrentEnc)
                            ))
                            Log.Debug(strLog)
                        else:
                            Log.Debug('******* SNIFF *******')
                            strLog = ''.join((
                                'We do not know the default encodings for ',
                                '%s' % (lang)
                            ))
                            Log.Debug(strLog)
                            strLog = ''.join((
                                'If you know this, then please go here: ',
                                'https://forums.plex.tv/discussion/94864',
                                ' and tell me'
                            ))
                            Log.Debug(strLog)
                else:
                    # We got ISO
                    # Does result so far match our list?
                    if sCurrentEnc == CP_Windows_ISO.cpISO[lang]:
                        Log.Debug('Origen CP is %s' % (sCurrentEnc))
                    else:
                        if CP_Windows_ISO.cpWindows[lang] != "Unknown":
                            sCurrentEnc = CP_Windows_ISO.cpISO[lang]
                            strLog = ''.join((
                                'Overriding detection due to languagecode',
                                ' in filename, and setting encoding to ',
                                '%s' % sCurrentEnc
                            ))
                            Log.Debug(strLog)
                        else:
                            Log.Debug('******* SNIFF *******')
                            strLog = ''.join((
                                'We do not know the default encodings for ',
                                '%s' % lang
                            ))
                            Log.Debug(strLog)
                            strLog = ''.join((
                                'If you know this, then please go here: ',
                                'https://forums.plex.tv/discussion/94864',
                                ' and tell me'
                            ))
                            Log.Debug(strLog)
        return sCurrentEnc
    except UnicodeDecodeError:
        Log.Debug('got unicode error with %s' % myFile)
        RevertBackup(myFile)
        return False


def FindEncChared(sMyFile, sModel):
    """ Detect the file encoding with chared """
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
            Log.Debug('%s Chared encoding detected as %s' % (sMyFile, myEnc))
            return myEnc
        else:
            Log.Debug('No Language module for %s' % model_file)
            return 'und'
    except:
        strLog = ''.join((
            'Unable to load charset detection model from ',
            '%s. ' % sModel,
            'Not supported.'
        ))
        Log.Critical(strLog)


def GetUsrEncPref():
    """ If no language was detected, we need to grap any User Prefs """
    return Prefs['PreferredCP']


def sGetFileLang(sMyFile):
    """
    Grap a language code from the filename, if present
    If a language code is present in the filename,
    then this function will return it
    If no language code is present, it'll return 'xx'
    """
    # Get the filename
    sFileName = os.path.splitext(sMyFile)[0]
    # Get language code if present, or else return 'xx'
    sFileName, sFileExtension = os.path.splitext(sFileName)
    myLang = sFileExtension[1:].lower()
    return Locale.Language.Match(myLang)


def bIsUTF_8(sMyFile):
    """ Returns true is file is in utf-8 """
    try:
        # Read the subtitle file
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


def sIsValid(sMyDir, sMediaFilename, sSubtitleFilename):
    """
    Returns a filename of a valid subtitle file,
    or 'null' if it's a no-go
    """
    try:
        Log.Debug('Checking if file %s is valid' % (sSubtitleFilename))
        # Valid list of subtitle ext.
        lValidList = Prefs['Valid_Ext'].upper().split()
        # Get the ext of the SubtitleFile
        sFileName, sFileExtension = os.path.splitext(sSubtitleFilename)
        # Is this a valid subtitle file?
        if (sFileExtension.upper() in lValidList):
            # It's a subtitle file, but is it for the mediafile?
            # Get filename without ext. of the media
            myMedia = os.path.splitext(os.path.basename(sMediaFilename))[0]
            # Get the name of the SubtitleFile
            sSRTName2 = os.path.splitext(sFileName)[0]
            strLog = ''.join((
                'Found a valid subtitle file named ',
                '"%s"' % sSubtitleFilename
            ))
            sSource = sMyDir + '/' + sSubtitleFilename
            if sFileName == myMedia:
                Log.Debug(strLog)
                return sSource
            elif myMedia == sSRTName2:
                Log.Debug(strLog)
                return sSource
            elif myMedia == sSRTName2.replace('.forced', ''):
                Log.Debug(strLog)
                return sSource
            elif myMedia == os.path.splitext(
                    sSRTName2.replace('.forced', ''))[0]:
                Log.Debug(strLog)
                return sSource
            else:
                return 'null'
        else:
            return 'null'
    except:
        strLog = ''.join((
            'An exception happened in function sIsValid in dir ',
            '%s ' % sMyDir,
            'for media ',
            '%s ' % sMediaFilename,
            'and file ',
            '%s' % sSubtitleFilename
        ))
        Log.Exception(strLog)
        return 'null'


def MakeBackup(file):
    """ Make the backup, if enabled """
    if Prefs['Make_Backup']:
        iCounter = 1
        sTarget = file + '.' + 'Srt2Utf-8'
        # Make sure we don't override an already existing backup
        while os.path.isfile(sTarget):
            sTarget = file + '.' + str(iCounter) + '.Srt2Utf-8'
            iCounter = iCounter + 1
        Log.Debug('Making a backup of %s as %s' % (file, sTarget))
        shutil.copyfile(file, sTarget)


def ValidatePrefs():
    """ Dummy to avoid bad logging """
    return


def RevertBackup(file):
    """ Revert the backup, if enabled """
    if Prefs['Make_Backup']:
        Log.Critical('** Reverting from backup, something went wrong here **')
        # Look back of a maximum of 250 backup's
        iCounter = 250
        sTarget = file + '.' + str(iCounter) + '.' + 'Srt2Utf-8'
        # Make sure we don't override an already existing backup
        while not os.path.isfile(sTarget):
            if iCounter == 0:
                sTarget = file + '.' + 'Srt2Utf-8'
            else:
                sTarget = file + '.' + str(iCounter) + '.' + 'Srt2Utf-8'
            iCounter = iCounter - 1
        Log.Debug('Reverting from backup of %s' % sTarget)
        shutil.copyfile(sTarget, file)
        # Cleanup bad tmp file
        if os.path.isfile(file + '.tmpPlex'):
            os.remove(file + '.tmpPlex')
        # Remove unneeded backup
        if os.path.isfile(sTarget):
            os.remove(sTarget)
    else:
        strLog = ''.join((
            '**** Something went wrong here, but backup has ',
            'been disabled....SIGH.....Your ',
            'fault, not mine!!!!! ****'
        ))
        Log.Critical(strLog)
