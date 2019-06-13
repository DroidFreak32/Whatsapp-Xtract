# -*- coding: utf-8 -*-
'''
WhatsApp Xtract v2.3.1
- WhatsApp Backup Messages Extractor for Android and iPhone

Released on April 25th, 2018

Tested with Whatsapp (Android) 2.18.46
Tested with Whatsapp (iPhone) 2.5.1

Changelog:

v2.3.1 (updated by depii - Jan 1, 2019)
- fixed message count
- output in one HTML-file per chat
- removed online media links
- fix linking to offline media, ppt media too
- new findfile functions, search now in subfolders
- added media duration
- added info for groups (creator and creation time)

v2.3 (updated by ztedd - Apr 25, 2018)
- fixed image preview to work with new Whatsapp database format
- some minor fixes

v2.2 (updated by Martina Weidner - Nov 17, 2012)
- now supports new emoji smileys
- (Android Version) hotfix for TypeError in b64encode
- (Android Version) decoded file won't be deleted even if it can't be opened

v2.1 (updated by Fabio Sangiacomo and Martina Weidner - May 7, 2012)
- improved install pyCrypto.bat
- added easy drag and drop possibility with whatsapp_xtract_drag'n'drop_database(s)_here.bat
- (Android Version) added support to fix corrupted android whatsapp database (needs sqlite3, for windows sqlite3.exe is contained in the archive)
- (Android Version) removed wrong extraction of owner in android version
- (Iphone Version) information from Z_METADATA table will be printed to shell
- (Iphone Version) fixed bug in support of older Iphone whatsapp databases

V2.0 (updated by Fabio Sangiacomo and Martina Weidner - Apr 26, 2012)
- supports WhatsApp DBs coming from both Android and iPhone platforms
- (Android Version) wa.db is optional
- (Android Version) now also crypted msgstore.db from the SD card can be imported
- chat list is sorted by the last sent message
- fixed bug that the script didn't work with python 3

V1.3 (updated by Martina Weidner - Apr 17, 2012)
- corrected linking of offline files (now linking according to media file size)

V1.2 (updated by Martina Weidner - Apr 5, 2012)
- media files also linked to offline files
- corrected hyperlinks

V1.1 (updated by Martina Weidner - Apr 5, 2012)
- changed database structure, Android only
- show contact names
- show smileys
- show images
- link / popup for images, video, audio, gps
- clickable links

V1.0 (created by Fabio Sangiacomo - Dec 10, 2011)
- first release, iPhone only:
  it takes in input the file "ChatStorage.sqlite",
  extracts chat sessions and the bare text 
- sortable js allows table sorting to make chat sessions easily readable

Usage:

For Android DB:
> python whatsapp_xtract.py msgstore.db -w wa.db
OR (if wa.db is unavailable)
> python whatsapp_xtract.py msgstore.db
OR (for crypted db)
> python whatsapp_xtract.py msgstore.db.crypt

For iPhone DB: (-w option is ignored)
> python whatsapp_xtract.py ChatStorage.sqlite

(C)opyright 2012 Fabio Sangiacomo <fabio.sangiacomo@digital-forensics.it>
(C)opyright 2012 Martina Weidner  <martina.weidner@freenet.ch>

Released under MIT licence

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in
all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
THE SOFTWARE.

'''

import sys, re, os, fnmatch, string, datetime, time, sqlite3, glob, webbrowser, base64, subprocess
from argparse import ArgumentParser

################################################################################
# Chatsession obj definition
class Chatsession:

    # init
    def __init__(self,pkcs,contactname,contactid,
                 contactmsgcount,contactunread,contactstatus,lastmessagedate):

        # if invalid params are passed, sets attributes to invalid values
        # primary key
        if pkcs == "" or pkcs is None:
            self.pk_cs = -1
        else:
            self.pk_cs = pkcs
            
        # contact nick
        if contactname == "" or contactname is None:
            self.contact_name = "N/A"
        else:
            self.contact_name = contactname
            
        # contact id
        if contactid == "" or contactid is None:
            self.contact_id = "N/A"
        else:
            self.contact_id = contactid
            
        # contact msg counter
        if contactmsgcount == "" or contactmsgcount is None:
            self.contact_msg_count = "N/A"
        else:
            self.contact_msg_count = contactmsgcount
            
        # contact unread msg
        if contactunread == "" or contactunread is None:
            self.contact_unread_msg = "N/A"
        else:
            self.contact_unread_msg = contactunread

        # contact status
        if contactstatus == "" or contactstatus is None:
            self.contact_status = "N/A"
        else:
            self.contact_status = contactstatus
            
        # contact last message date
        if lastmessagedate == "" or lastmessagedate is None or lastmessagedate == 0:
            self.last_message_date = " N/A" #space is necessary for that the empty chats are placed at the end on sorting
        else:
            try:
                if mode == IPHONE:
                    lastmessagedate = str(lastmessagedate)
                    if lastmessagedate.find(".") > -1: #if timestamp is not like "304966548", but like "306350664.792749", then just use the numbers in front of the "."
                        lastmessagedate = lastmessagedate[:lastmessagedate.find(".")]
                    self.last_message_date = datetime.datetime.fromtimestamp(int(lastmessagedate)+11323*60*1440)
                elif mode == ANDROID:
                    msgdate = str(lastmessagedate)
                    # cut last 3 digits (microseconds)
                    msgdate = msgdate[:-3]
                    self.last_message_date = datetime.datetime.fromtimestamp(int(msgdate))
                self.last_message_date = str( self.last_message_date )
            except (TypeError, ValueError) as msg:
                print('Error while reading chat #{}: {}'.format(self.pk_cs,msg))
                self.last_message_date = " N/A error"

        # chat session messages
        self.msg_list = []

    # comparison operator
    def __cmp__(self, other):
        if self.pk_cs == other.pk_cs:
                return 0
        return 1

################################################################################
# Message obj definition
class Message:

    # init
    def __init__(self,pkmsg,fromme,keyid,msgdate,text,contactfrom,msgstatus,
                 localurl, mediaurl,mediathumb,mediathumblocalurl,mediawatype,mediasize,mediaduration,latitude,longitude,vcardname,vcardstring):

        # if invalid params are passed, sets attributes to invalid values
        # primary key
        if pkmsg == "" or pkmsg is None:
            self.pk_msg = -1
        else:
            self.pk_msg = pkmsg

        # msg key id
        if keyid == "" or keyid is None:
            self.keyid = None
        else:
            self.key_id = keyid
            
        # "from me" flag
        if fromme == "" or fromme is None:
            self.from_me = -1
        else:
            self.from_me = fromme
            
        # message timestamp
        if msgdate == "" or msgdate is None or msgdate == 0:
            self.msg_date = "N/A"
        else:
            try:
                if mode == IPHONE:
                    msgdate = str(msgdate)
                    if msgdate.find(".") > -1: #if timestamp is not like "304966548", but like "306350664.792749", then just use the numbers in front of the "."
                        msgdate = msgdate[:msgdate.find(".")]
                    self.msg_date = datetime.datetime.fromtimestamp(int(msgdate)+11323*60*1440)
                elif mode == ANDROID:
                    msgdate = str(msgdate)
                    # cut last 3 digits (microseconds)
                    msgdate = msgdate[:-3]
                    self.msg_date = datetime.datetime.fromtimestamp(int(msgdate))
            except (TypeError, ValueError) as msg:
                print('Error while reading message #{}: {}'.format(self.pk_msg,msg))
                self.msg_date = "N/A error"

        # message text
        if text == "" or text is None:
            self.msg_text = "N/A"
        else:
            self.msg_text = text
        # contact from
        if contactfrom == "" or contactfrom is None:
            self.contact_from = "N/A"
        else:
            self.contact_from = contactfrom
            
        # media
        if localurl == "" or localurl is None:
            self.local_url = ""
        else:
            self.local_url = localurl  
        if mediaurl == "" or mediaurl is None:
            self.media_url = ""
        else:
            self.media_url = mediaurl            
        if mediathumb == "" or mediathumb is None:
            self.media_thumb = ""
        else:
            self.media_thumb = mediathumb
        if mediathumblocalurl == "" or mediathumblocalurl is None:
            self.media_thumb_local_url = ""
        else:
            self.media_thumb_local_url = mediathumblocalurl
        if mediawatype == "" or mediawatype is None:
            self.media_wa_type = ""
        else:
            self.media_wa_type = mediawatype            
        if mediasize == "" or mediasize is None:
            self.media_size = ""
        else:
            self.media_size = mediasize
        if mediaduration == "" or mediaduration is None:
            self.media_duration = ""
        else:
            self.media_duration = mediaduration

        #status
        if msgstatus == "" or msgstatus is None:
            self.status = "N/A"
        else:
            self.status = msgstatus
        
        #GPS
        if latitude == "" or latitude is None:
            self.latitude = ""
        else:
            self.latitude = latitude
        if longitude == "" or longitude is None:
            self.longitude = ""
        else:
            self.longitude = longitude
        
        #VCARD
        if vcardname == "" or vcardname is None:
            self.vcard_name = ""
        else:
            self.vcard_name = vcardname
        if vcardstring == "" or vcardstring is None:
            self.vcard_string = ""
        else:
            self.vcard_string = vcardstring

    # comparison operator
    def __cmp__(self, other):
        if self.pk_msg == other.pk_msg:
                return 0
        return 1
    
################################################################################
# Smileys conversion function
def convertsmileys_python3 (text):
    newtext = str(text)
    
    # old emojis
    newtext = newtext.replace('\ue415', '<img src="data/emoji/e415.png" alt=""/>')
    newtext = newtext.replace('\ue056', '<img src="data/emoji/e056.png" alt=""/>')
    newtext = newtext.replace('\ue057', '<img src="data/emoji/e057.png" alt=""/>')
    newtext = newtext.replace('\ue414', '<img src="data/emoji/e414.png" alt=""/>')
    newtext = newtext.replace('\ue405', '<img src="data/emoji/e405.png" alt=""/>')
    newtext = newtext.replace('\ue106', '<img src="data/emoji/e106.png" alt=""/>')
    newtext = newtext.replace('\ue418', '<img src="data/emoji/e418.png" alt=""/>')

    newtext = newtext.replace('\ue417', '<img src="data/emoji/e417.png" alt=""/>')
    newtext = newtext.replace('\ue40d', '<img src="data/emoji/e40d.png" alt=""/>')
    newtext = newtext.replace('\ue40a', '<img src="data/emoji/e40a.png" alt=""/>')
    newtext = newtext.replace('\ue404', '<img src="data/emoji/e404.png" alt=""/>')
    newtext = newtext.replace('\ue105', '<img src="data/emoji/e105.png" alt=""/>')
    newtext = newtext.replace('\ue409', '<img src="data/emoji/e409.png" alt=""/>')
    newtext = newtext.replace('\ue40e', '<img src="data/emoji/e40e.png" alt=""/>')

    newtext = newtext.replace('\ue402', '<img src="data/emoji/e402.png" alt=""/>')
    newtext = newtext.replace('\ue108', '<img src="data/emoji/e108.png" alt=""/>')
    newtext = newtext.replace('\ue403', '<img src="data/emoji/e403.png" alt=""/>')
    newtext = newtext.replace('\ue058', '<img src="data/emoji/e058.png" alt=""/>')
    newtext = newtext.replace('\ue407', '<img src="data/emoji/e407.png" alt=""/>')
    newtext = newtext.replace('\ue401', '<img src="data/emoji/e401.png" alt=""/>')
    newtext = newtext.replace('\ue40f', '<img src="data/emoji/e40f.png" alt=""/>')

    newtext = newtext.replace('\ue40b', '<img src="data/emoji/e40b.png" alt=""/>')
    newtext = newtext.replace('\ue406', '<img src="data/emoji/e406.png" alt=""/>')
    newtext = newtext.replace('\ue413', '<img src="data/emoji/e413.png" alt=""/>')
    newtext = newtext.replace('\ue411', '<img src="data/emoji/e411.png" alt=""/>')
    newtext = newtext.replace('\ue412', '<img src="data/emoji/e412.png" alt=""/>')
    newtext = newtext.replace('\ue410', '<img src="data/emoji/e410.png" alt=""/>')
    newtext = newtext.replace('\ue107', '<img src="data/emoji/e107.png" alt=""/>')

    newtext = newtext.replace('\ue059', '<img src="data/emoji/e059.png" alt=""/>')
    newtext = newtext.replace('\ue416', '<img src="data/emoji/e416.png" alt=""/>')
    newtext = newtext.replace('\ue408', '<img src="data/emoji/e408.png" alt=""/>')
    newtext = newtext.replace('\ue40c', '<img src="data/emoji/e40c.png" alt=""/>')
    newtext = newtext.replace('\ue11a', '<img src="data/emoji/e11a.png" alt=""/>')
    newtext = newtext.replace('\ue10c', '<img src="data/emoji/e10c.png" alt=""/>')
    newtext = newtext.replace('\ue32c', '<img src="data/emoji/e32c.png" alt=""/>')

    newtext = newtext.replace('\ue32a', '<img src="data/emoji/e32a.png" alt=""/>')
    newtext = newtext.replace('\ue32d', '<img src="data/emoji/e32d.png" alt=""/>')
    newtext = newtext.replace('\ue328', '<img src="data/emoji/e328.png" alt=""/>')
    newtext = newtext.replace('\ue32b', '<img src="data/emoji/e32b.png" alt=""/>')
    newtext = newtext.replace('\ue022', '<img src="data/emoji/e022.png" alt=""/>')
    newtext = newtext.replace('\ue023', '<img src="data/emoji/e023.png" alt=""/>')
    newtext = newtext.replace('\ue327', '<img src="data/emoji/e327.png" alt=""/>')

    newtext = newtext.replace('\ue329', '<img src="data/emoji/e329.png" alt=""/>')
    newtext = newtext.replace('\ue32e', '<img src="data/emoji/e32e.png" alt=""/>')
    newtext = newtext.replace('\ue32f', '<img src="data/emoji/e32f.png" alt=""/>')
    newtext = newtext.replace('\ue335', '<img src="data/emoji/e335.png" alt=""/>')
    newtext = newtext.replace('\ue334', '<img src="data/emoji/e334.png" alt=""/>')
    newtext = newtext.replace('\ue021', '<img src="data/emoji/e021.png" alt=""/>')
    newtext = newtext.replace('\ue337', '<img src="data/emoji/e337.png" alt=""/>')

    newtext = newtext.replace('\ue020', '<img src="data/emoji/e020.png" alt=""/>')
    newtext = newtext.replace('\ue336', '<img src="data/emoji/e336.png" alt=""/>')
    newtext = newtext.replace('\ue13c', '<img src="data/emoji/e13c.png" alt=""/>')
    newtext = newtext.replace('\ue330', '<img src="data/emoji/e330.png" alt=""/>')
    newtext = newtext.replace('\ue331', '<img src="data/emoji/e331.png" alt=""/>')
    newtext = newtext.replace('\ue326', '<img src="data/emoji/e326.png" alt=""/>')
    newtext = newtext.replace('\ue03e', '<img src="data/emoji/e03e.png" alt=""/>')

    newtext = newtext.replace('\ue11d', '<img src="data/emoji/e11d.png" alt=""/>')
    newtext = newtext.replace('\ue05a', '<img src="data/emoji/e05a.png" alt=""/>')
    newtext = newtext.replace('\ue00e', '<img src="data/emoji/e00e.png" alt=""/>')
    newtext = newtext.replace('\ue421', '<img src="data/emoji/e421.png" alt=""/>')
    newtext = newtext.replace('\ue420', '<img src="data/emoji/e420.png" alt=""/>')
    newtext = newtext.replace('\ue00d', '<img src="data/emoji/e00d.png" alt=""/>')
    newtext = newtext.replace('\ue010', '<img src="data/emoji/e010.png" alt=""/>')

    newtext = newtext.replace('\ue011', '<img src="data/emoji/e011.png" alt=""/>')
    newtext = newtext.replace('\ue41e', '<img src="data/emoji/e41e.png" alt=""/>')
    newtext = newtext.replace('\ue012', '<img src="data/emoji/e012.png" alt=""/>')
    newtext = newtext.replace('\ue422', '<img src="data/emoji/e422.png" alt=""/>')
    newtext = newtext.replace('\ue22e', '<img src="data/emoji/e22e.png" alt=""/>')
    newtext = newtext.replace('\ue22f', '<img src="data/emoji/e22f.png" alt=""/>')
    newtext = newtext.replace('\ue231', '<img src="data/emoji/e231.png" alt=""/>')

    newtext = newtext.replace('\ue230', '<img src="data/emoji/e230.png" alt=""/>')
    newtext = newtext.replace('\ue427', '<img src="data/emoji/e427.png" alt=""/>')
    newtext = newtext.replace('\ue41d', '<img src="data/emoji/e41d.png" alt=""/>')
    newtext = newtext.replace('\ue00f', '<img src="data/emoji/e00f.png" alt=""/>')
    newtext = newtext.replace('\ue41f', '<img src="data/emoji/e41f.png" alt=""/>')
    newtext = newtext.replace('\ue14c', '<img src="data/emoji/e14c.png" alt=""/>')
    newtext = newtext.replace('\ue201', '<img src="data/emoji/e201.png" alt=""/>')

    newtext = newtext.replace('\ue115', '<img src="data/emoji/e115.png" alt=""/>')
    newtext = newtext.replace('\ue428', '<img src="data/emoji/e428.png" alt=""/>')
    newtext = newtext.replace('\ue51f', '<img src="data/emoji/e51f.png" alt=""/>')
    newtext = newtext.replace('\ue429', '<img src="data/emoji/e429.png" alt=""/>')
    newtext = newtext.replace('\ue424', '<img src="data/emoji/e424.png" alt=""/>')
    newtext = newtext.replace('\ue423', '<img src="data/emoji/e423.png" alt=""/>')
    newtext = newtext.replace('\ue253', '<img src="data/emoji/e253.png" alt=""/>')

    newtext = newtext.replace('\ue426', '<img src="data/emoji/e426.png" alt=""/>')
    newtext = newtext.replace('\ue111', '<img src="data/emoji/e111.png" alt=""/>')
    newtext = newtext.replace('\ue425', '<img src="data/emoji/e425.png" alt=""/>')
    newtext = newtext.replace('\ue31e', '<img src="data/emoji/e31e.png" alt=""/>')
    newtext = newtext.replace('\ue31f', '<img src="data/emoji/e31f.png" alt=""/>')
    newtext = newtext.replace('\ue31d', '<img src="data/emoji/e31d.png" alt=""/>')
    newtext = newtext.replace('\ue001', '<img src="data/emoji/e001.png" alt=""/>')

    newtext = newtext.replace('\ue002', '<img src="data/emoji/e002.png" alt=""/>')
    newtext = newtext.replace('\ue005', '<img src="data/emoji/e005.png" alt=""/>')
    newtext = newtext.replace('\ue004', '<img src="data/emoji/e004.png" alt=""/>')
    newtext = newtext.replace('\ue51a', '<img src="data/emoji/e51a.png" alt=""/>')
    newtext = newtext.replace('\ue519', '<img src="data/emoji/e519.png" alt=""/>')
    newtext = newtext.replace('\ue518', '<img src="data/emoji/e518.png" alt=""/>')
    newtext = newtext.replace('\ue515', '<img src="data/emoji/e515.png" alt=""/>')

    newtext = newtext.replace('\ue516', '<img src="data/emoji/e516.png" alt=""/>')
    newtext = newtext.replace('\ue517', '<img src="data/emoji/e517.png" alt=""/>')
    newtext = newtext.replace('\ue51b', '<img src="data/emoji/e51b.png" alt=""/>')
    newtext = newtext.replace('\ue152', '<img src="data/emoji/e152.png" alt=""/>')
    newtext = newtext.replace('\ue04e', '<img src="data/emoji/e04e.png" alt=""/>')
    newtext = newtext.replace('\ue51c', '<img src="data/emoji/e51c.png" alt=""/>')
    newtext = newtext.replace('\ue51e', '<img src="data/emoji/e51e.png" alt=""/>')

    newtext = newtext.replace('\ue11c', '<img src="data/emoji/e11c.png" alt=""/>')
    newtext = newtext.replace('\ue536', '<img src="data/emoji/e536.png" alt=""/>')
    newtext = newtext.replace('\ue003', '<img src="data/emoji/e003.png" alt=""/>')
    newtext = newtext.replace('\ue41c', '<img src="data/emoji/e41c.png" alt=""/>')
    newtext = newtext.replace('\ue41b', '<img src="data/emoji/e41b.png" alt=""/>')
    newtext = newtext.replace('\ue419', '<img src="data/emoji/e419.png" alt=""/>')
    newtext = newtext.replace('\ue41a', '<img src="data/emoji/e41a.png" alt=""/>')

    newtext = newtext.replace('\ue04a', '<img src="data/emoji/e04a.png" alt=""/>')
    newtext = newtext.replace('\ue04b', '<img src="data/emoji/e04b.png" alt=""/>')
    newtext = newtext.replace('\ue049', '<img src="data/emoji/e049.png" alt=""/>')
    newtext = newtext.replace('\ue048', '<img src="data/emoji/e048.png" alt=""/>')
    newtext = newtext.replace('\ue04c', '<img src="data/emoji/e04c.png" alt=""/>')
    newtext = newtext.replace('\ue13d', '<img src="data/emoji/e13d.png" alt=""/>')
    newtext = newtext.replace('\ue443', '<img src="data/emoji/e443.png" alt=""/>')

    newtext = newtext.replace('\ue43e', '<img src="data/emoji/e43e.png" alt=""/>')
    newtext = newtext.replace('\ue04f', '<img src="data/emoji/e04f.png" alt=""/>')
    newtext = newtext.replace('\ue052', '<img src="data/emoji/e052.png" alt=""/>')
    newtext = newtext.replace('\ue053', '<img src="data/emoji/e053.png" alt=""/>')
    newtext = newtext.replace('\ue524', '<img src="data/emoji/e524.png" alt=""/>')
    newtext = newtext.replace('\ue52c', '<img src="data/emoji/e52c.png" alt=""/>')
    newtext = newtext.replace('\ue52a', '<img src="data/emoji/e52a.png" alt=""/>')

    newtext = newtext.replace('\ue531', '<img src="data/emoji/e531.png" alt=""/>')
    newtext = newtext.replace('\ue050', '<img src="data/emoji/e050.png" alt=""/>')
    newtext = newtext.replace('\ue527', '<img src="data/emoji/e527.png" alt=""/>')
    newtext = newtext.replace('\ue051', '<img src="data/emoji/e051.png" alt=""/>')
    newtext = newtext.replace('\ue10b', '<img src="data/emoji/e10b.png" alt=""/>')
    newtext = newtext.replace('\ue52b', '<img src="data/emoji/e52b.png" alt=""/>')
    newtext = newtext.replace('\ue52f', '<img src="data/emoji/e52f.png" alt=""/>')

    newtext = newtext.replace('\ue528', '<img src="data/emoji/e528.png" alt=""/>')
    newtext = newtext.replace('\ue01a', '<img src="data/emoji/e01a.png" alt=""/>')
    newtext = newtext.replace('\ue134', '<img src="data/emoji/e134.png" alt=""/>')
    newtext = newtext.replace('\ue530', '<img src="data/emoji/e530.png" alt=""/>')
    newtext = newtext.replace('\ue529', '<img src="data/emoji/e529.png" alt=""/>')
    newtext = newtext.replace('\ue526', '<img src="data/emoji/e526.png" alt=""/>')
    newtext = newtext.replace('\ue52d', '<img src="data/emoji/e52d.png" alt=""/>')

    newtext = newtext.replace('\ue521', '<img src="data/emoji/e521.png" alt=""/>')
    newtext = newtext.replace('\ue523', '<img src="data/emoji/e523.png" alt=""/>')
    newtext = newtext.replace('\ue52e', '<img src="data/emoji/e52e.png" alt=""/>')
    newtext = newtext.replace('\ue055', '<img src="data/emoji/e055.png" alt=""/>')
    newtext = newtext.replace('\ue525', '<img src="data/emoji/e525.png" alt=""/>')
    newtext = newtext.replace('\ue10a', '<img src="data/emoji/e10a.png" alt=""/>')
    newtext = newtext.replace('\ue109', '<img src="data/emoji/e109.png" alt=""/>')

    newtext = newtext.replace('\ue522', '<img src="data/emoji/e522.png" alt=""/>')
    newtext = newtext.replace('\ue019', '<img src="data/emoji/e019.png" alt=""/>')
    newtext = newtext.replace('\ue054', '<img src="data/emoji/e054.png" alt=""/>')
    newtext = newtext.replace('\ue520', '<img src="data/emoji/e520.png" alt=""/>')
    newtext = newtext.replace('\ue306', '<img src="data/emoji/e306.png" alt=""/>')
    newtext = newtext.replace('\ue030', '<img src="data/emoji/e030.png" alt=""/>')
    newtext = newtext.replace('\ue304', '<img src="data/emoji/e304.png" alt=""/>')

    newtext = newtext.replace('\ue110', '<img src="data/emoji/e110.png" alt=""/>')
    newtext = newtext.replace('\ue032', '<img src="data/emoji/e032.png" alt=""/>')
    newtext = newtext.replace('\ue305', '<img src="data/emoji/e305.png" alt=""/>')
    newtext = newtext.replace('\ue303', '<img src="data/emoji/e303.png" alt=""/>')
    newtext = newtext.replace('\ue118', '<img src="data/emoji/e118.png" alt=""/>')
    newtext = newtext.replace('\ue447', '<img src="data/emoji/e447.png" alt=""/>')
    newtext = newtext.replace('\ue119', '<img src="data/emoji/e119.png" alt=""/>')

    newtext = newtext.replace('\ue307', '<img src="data/emoji/e307.png" alt=""/>')
    newtext = newtext.replace('\ue308', '<img src="data/emoji/e308.png" alt=""/>')
    newtext = newtext.replace('\ue444', '<img src="data/emoji/e444.png" alt=""/>')
    newtext = newtext.replace('\ue441', '<img src="data/emoji/e441.png" alt=""/>')

    newtext = newtext.replace('\ue436', '<img src="data/emoji/e436.png" alt=""/>')
    newtext = newtext.replace('\ue437', '<img src="data/emoji/e437.png" alt=""/>')
    newtext = newtext.replace('\ue438', '<img src="data/emoji/e438.png" alt=""/>')
    newtext = newtext.replace('\ue43a', '<img src="data/emoji/e43a.png" alt=""/>')
    newtext = newtext.replace('\ue439', '<img src="data/emoji/e439.png" alt=""/>')
    newtext = newtext.replace('\ue43b', '<img src="data/emoji/e43b.png" alt=""/>')
    newtext = newtext.replace('\ue117', '<img src="data/emoji/e117.png" alt=""/>')

    newtext = newtext.replace('\ue440', '<img src="data/emoji/e440.png" alt=""/>')
    newtext = newtext.replace('\ue442', '<img src="data/emoji/e442.png" alt=""/>')
    newtext = newtext.replace('\ue446', '<img src="data/emoji/e446.png" alt=""/>')
    newtext = newtext.replace('\ue445', '<img src="data/emoji/e445.png" alt=""/>')
    newtext = newtext.replace('\ue11b', '<img src="data/emoji/e11b.png" alt=""/>')
    newtext = newtext.replace('\ue448', '<img src="data/emoji/e448.png" alt=""/>')
    newtext = newtext.replace('\ue033', '<img src="data/emoji/e033.png" alt=""/>')

    newtext = newtext.replace('\ue112', '<img src="data/emoji/e112.png" alt=""/>')
    newtext = newtext.replace('\ue325', '<img src="data/emoji/e325.png" alt=""/>')
    newtext = newtext.replace('\ue312', '<img src="data/emoji/e312.png" alt=""/>')
    newtext = newtext.replace('\ue310', '<img src="data/emoji/e310.png" alt=""/>')
    newtext = newtext.replace('\ue126', '<img src="data/emoji/e126.png" alt=""/>')
    newtext = newtext.replace('\ue127', '<img src="data/emoji/e127.png" alt=""/>')
    newtext = newtext.replace('\ue008', '<img src="data/emoji/e008.png" alt=""/>')

    newtext = newtext.replace('\ue03d', '<img src="data/emoji/e03d.png" alt=""/>')
    newtext = newtext.replace('\ue00c', '<img src="data/emoji/e00c.png" alt=""/>')
    newtext = newtext.replace('\ue12a', '<img src="data/emoji/e12a.png" alt=""/>')
    newtext = newtext.replace('\ue00a', '<img src="data/emoji/e00a.png" alt=""/>')
    newtext = newtext.replace('\ue00b', '<img src="data/emoji/e00b.png" alt=""/>')
    newtext = newtext.replace('\ue009', '<img src="data/emoji/e009.png" alt=""/>')
    newtext = newtext.replace('\ue316', '<img src="data/emoji/e316.png" alt=""/>')

    newtext = newtext.replace('\ue129', '<img src="data/emoji/e129.png" alt=""/>')
    newtext = newtext.replace('\ue141', '<img src="data/emoji/e141.png" alt=""/>')
    newtext = newtext.replace('\ue142', '<img src="data/emoji/e142.png" alt=""/>')
    newtext = newtext.replace('\ue317', '<img src="data/emoji/e317.png" alt=""/>')
    newtext = newtext.replace('\ue128', '<img src="data/emoji/e128.png" alt=""/>')
    newtext = newtext.replace('\ue14b', '<img src="data/emoji/e14b.png" alt=""/>')
    newtext = newtext.replace('\ue211', '<img src="data/emoji/e211.png" alt=""/>')

    newtext = newtext.replace('\ue114', '<img src="data/emoji/e114.png" alt=""/>')
    newtext = newtext.replace('\ue145', '<img src="data/emoji/e145.png" alt=""/>')
    newtext = newtext.replace('\ue144', '<img src="data/emoji/e144.png" alt=""/>')
    newtext = newtext.replace('\ue03f', '<img src="data/emoji/e03f.png" alt=""/>')
    newtext = newtext.replace('\ue313', '<img src="data/emoji/e313.png" alt=""/>')
    newtext = newtext.replace('\ue116', '<img src="data/emoji/e116.png" alt=""/>')
    newtext = newtext.replace('\ue10f', '<img src="data/emoji/e10f.png" alt=""/>')

    newtext = newtext.replace('\ue104', '<img src="data/emoji/e104.png" alt=""/>')
    newtext = newtext.replace('\ue103', '<img src="data/emoji/e103.png" alt=""/>')
    newtext = newtext.replace('\ue101', '<img src="data/emoji/e101.png" alt=""/>')
    newtext = newtext.replace('\ue102', '<img src="data/emoji/e102.png" alt=""/>')
    newtext = newtext.replace('\ue13f', '<img src="data/emoji/e13f.png" alt=""/>')
    newtext = newtext.replace('\ue140', '<img src="data/emoji/e140.png" alt=""/>')
    newtext = newtext.replace('\ue11f', '<img src="data/emoji/e11f.png" alt=""/>')

    newtext = newtext.replace('\ue12f', '<img src="data/emoji/e12f.png" alt=""/>')
    newtext = newtext.replace('\ue031', '<img src="data/emoji/e031.png" alt=""/>')
    newtext = newtext.replace('\ue30e', '<img src="data/emoji/e30e.png" alt=""/>')
    newtext = newtext.replace('\ue311', '<img src="data/emoji/e311.png" alt=""/>')
    newtext = newtext.replace('\ue113', '<img src="data/emoji/e113.png" alt=""/>')
    newtext = newtext.replace('\ue30f', '<img src="data/emoji/e30f.png" alt=""/>')
    newtext = newtext.replace('\ue13b', '<img src="data/emoji/e13b.png" alt=""/>')

    newtext = newtext.replace('\ue42b', '<img src="data/emoji/e42b.png" alt=""/>')
    newtext = newtext.replace('\ue42a', '<img src="data/emoji/e42a.png" alt=""/>')
    newtext = newtext.replace('\ue018', '<img src="data/emoji/e018.png" alt=""/>')
    newtext = newtext.replace('\ue016', '<img src="data/emoji/e016.png" alt=""/>')
    newtext = newtext.replace('\ue015', '<img src="data/emoji/e015.png" alt=""/>')
    newtext = newtext.replace('\ue014', '<img src="data/emoji/e014.png" alt=""/>')
    newtext = newtext.replace('\ue42c', '<img src="data/emoji/e42c.png" alt=""/>')

    newtext = newtext.replace('\ue42d', '<img src="data/emoji/e42d.png" alt=""/>')
    newtext = newtext.replace('\ue017', '<img src="data/emoji/e017.png" alt=""/>')
    newtext = newtext.replace('\ue013', '<img src="data/emoji/e013.png" alt=""/>')
    newtext = newtext.replace('\ue20e', '<img src="data/emoji/e20e.png" alt=""/>')
    newtext = newtext.replace('\ue20c', '<img src="data/emoji/e20c.png" alt=""/>')
    newtext = newtext.replace('\ue20f', '<img src="data/emoji/e20f.png" alt=""/>')
    newtext = newtext.replace('\ue20d', '<img src="data/emoji/e20d.png" alt=""/>')

    newtext = newtext.replace('\ue131', '<img src="data/emoji/e131.png" alt=""/>')
    newtext = newtext.replace('\ue12b', '<img src="data/emoji/e12b.png" alt=""/>')
    newtext = newtext.replace('\ue130', '<img src="data/emoji/e130.png" alt=""/>')
    newtext = newtext.replace('\ue12d', '<img src="data/emoji/e12d.png" alt=""/>')
    newtext = newtext.replace('\ue324', '<img src="data/emoji/e324.png" alt=""/>')
    newtext = newtext.replace('\ue301', '<img src="data/emoji/e301.png" alt=""/>')
    newtext = newtext.replace('\ue148', '<img src="data/emoji/e148.png" alt=""/>')

    newtext = newtext.replace('\ue502', '<img src="data/emoji/e502.png" alt=""/>')
    newtext = newtext.replace('\ue03c', '<img src="data/emoji/e03c.png" alt=""/>')
    newtext = newtext.replace('\ue30a', '<img src="data/emoji/e30a.png" alt=""/>')
    newtext = newtext.replace('\ue042', '<img src="data/emoji/e042.png" alt=""/>')
    newtext = newtext.replace('\ue040', '<img src="data/emoji/e040.png" alt=""/>')
    newtext = newtext.replace('\ue041', '<img src="data/emoji/e041.png" alt=""/>')
    newtext = newtext.replace('\ue12c', '<img src="data/emoji/e12c.png" alt=""/>')

    newtext = newtext.replace('\ue007', '<img src="data/emoji/e007.png" alt=""/>')
    newtext = newtext.replace('\ue31a', '<img src="data/emoji/e31a.png" alt=""/>')
    newtext = newtext.replace('\ue13e', '<img src="data/emoji/e13e.png" alt=""/>')
    newtext = newtext.replace('\ue31b', '<img src="data/emoji/e31b.png" alt=""/>')
    newtext = newtext.replace('\ue006', '<img src="data/emoji/e006.png" alt=""/>')
    newtext = newtext.replace('\ue302', '<img src="data/emoji/e302.png" alt=""/>')
    newtext = newtext.replace('\ue319', '<img src="data/emoji/e319.png" alt=""/>')

    newtext = newtext.replace('\ue321', '<img src="data/emoji/e321.png" alt=""/>')
    newtext = newtext.replace('\ue322', '<img src="data/emoji/e322.png" alt=""/>')
    newtext = newtext.replace('\ue314', '<img src="data/emoji/e314.png" alt=""/>')
    newtext = newtext.replace('\ue503', '<img src="data/emoji/e503.png" alt=""/>')
    newtext = newtext.replace('\ue10e', '<img src="data/emoji/e10e.png" alt=""/>')
    newtext = newtext.replace('\ue318', '<img src="data/emoji/e318.png" alt=""/>')
    newtext = newtext.replace('\ue43c', '<img src="data/emoji/e43c.png" alt=""/>')

    newtext = newtext.replace('\ue11e', '<img src="data/emoji/e11e.png" alt=""/>')
    newtext = newtext.replace('\ue323', '<img src="data/emoji/e323.png" alt=""/>')
    newtext = newtext.replace('\ue31c', '<img src="data/emoji/e31c.png" alt=""/>')
    newtext = newtext.replace('\ue034', '<img src="data/emoji/e034.png" alt=""/>')
    newtext = newtext.replace('\ue035', '<img src="data/emoji/e035.png" alt=""/>')
    newtext = newtext.replace('\ue045', '<img src="data/emoji/e045.png" alt=""/>')
    newtext = newtext.replace('\ue338', '<img src="data/emoji/e338.png" alt=""/>')

    newtext = newtext.replace('\ue047', '<img src="data/emoji/e047.png" alt=""/>')
    newtext = newtext.replace('\ue30c', '<img src="data/emoji/e30c.png" alt=""/>')
    newtext = newtext.replace('\ue044', '<img src="data/emoji/e044.png" alt=""/>')
    newtext = newtext.replace('\ue30b', '<img src="data/emoji/e30b.png" alt=""/>')
    newtext = newtext.replace('\ue043', '<img src="data/emoji/e043.png" alt=""/>')
    newtext = newtext.replace('\ue120', '<img src="data/emoji/e120.png" alt=""/>')
    newtext = newtext.replace('\ue33b', '<img src="data/emoji/e33b.png" alt=""/>')

    newtext = newtext.replace('\ue33f', '<img src="data/emoji/e33f.png" alt=""/>')
    newtext = newtext.replace('\ue341', '<img src="data/emoji/e341.png" alt=""/>')
    newtext = newtext.replace('\ue34c', '<img src="data/emoji/e34c.png" alt=""/>')
    newtext = newtext.replace('\ue344', '<img src="data/emoji/e344.png" alt=""/>')
    newtext = newtext.replace('\ue342', '<img src="data/emoji/e342.png" alt=""/>')
    newtext = newtext.replace('\ue33d', '<img src="data/emoji/e33d.png" alt=""/>')
    newtext = newtext.replace('\ue33e', '<img src="data/emoji/e33e.png" alt=""/>')

    newtext = newtext.replace('\ue340', '<img src="data/emoji/e340.png" alt=""/>')
    newtext = newtext.replace('\ue34d', '<img src="data/emoji/e34d.png" alt=""/>')
    newtext = newtext.replace('\ue339', '<img src="data/emoji/e339.png" alt=""/>')
    newtext = newtext.replace('\ue147', '<img src="data/emoji/e147.png" alt=""/>')
    newtext = newtext.replace('\ue343', '<img src="data/emoji/e343.png" alt=""/>')
    newtext = newtext.replace('\ue33c', '<img src="data/emoji/e33c.png" alt=""/>')
    newtext = newtext.replace('\ue33a', '<img src="data/emoji/e33a.png" alt=""/>')

    newtext = newtext.replace('\ue43f', '<img src="data/emoji/e43f.png" alt=""/>')
    newtext = newtext.replace('\ue34b', '<img src="data/emoji/e34b.png" alt=""/>')
    newtext = newtext.replace('\ue046', '<img src="data/emoji/e046.png" alt=""/>')
    newtext = newtext.replace('\ue345', '<img src="data/emoji/e345.png" alt=""/>')
    newtext = newtext.replace('\ue346', '<img src="data/emoji/e346.png" alt=""/>')
    newtext = newtext.replace('\ue348', '<img src="data/emoji/e348.png" alt=""/>')
    newtext = newtext.replace('\ue347', '<img src="data/emoji/e347.png" alt=""/>')

    newtext = newtext.replace('\ue34a', '<img src="data/emoji/e34a.png" alt=""/>')
    newtext = newtext.replace('\ue349', '<img src="data/emoji/e349.png" alt=""/>')

    newtext = newtext.replace('\ue036', '<img src="data/emoji/e036.png" alt=""/>')
    newtext = newtext.replace('\ue157', '<img src="data/emoji/e157.png" alt=""/>')
    newtext = newtext.replace('\ue038', '<img src="data/emoji/e038.png" alt=""/>')
    newtext = newtext.replace('\ue153', '<img src="data/emoji/e153.png" alt=""/>')
    newtext = newtext.replace('\ue155', '<img src="data/emoji/e155.png" alt=""/>')
    newtext = newtext.replace('\ue14d', '<img src="data/emoji/e14d.png" alt=""/>')
    newtext = newtext.replace('\ue156', '<img src="data/emoji/e156.png" alt=""/>')

    newtext = newtext.replace('\ue501', '<img src="data/emoji/e501.png" alt=""/>')
    newtext = newtext.replace('\ue158', '<img src="data/emoji/e158.png" alt=""/>')
    newtext = newtext.replace('\ue43d', '<img src="data/emoji/e43d.png" alt=""/>')
    newtext = newtext.replace('\ue037', '<img src="data/emoji/e037.png" alt=""/>')
    newtext = newtext.replace('\ue504', '<img src="data/emoji/e504.png" alt=""/>')
    newtext = newtext.replace('\ue44a', '<img src="data/emoji/e44a.png" alt=""/>')
    newtext = newtext.replace('\ue146', '<img src="data/emoji/e146.png" alt=""/>')

    newtext = newtext.replace('\ue50a', '<img src="data/emoji/e50a.png" alt=""/>')
    newtext = newtext.replace('\ue505', '<img src="data/emoji/e505.png" alt=""/>')
    newtext = newtext.replace('\ue506', '<img src="data/emoji/e506.png" alt=""/>')
    newtext = newtext.replace('\ue122', '<img src="data/emoji/e122.png" alt=""/>')
    newtext = newtext.replace('\ue508', '<img src="data/emoji/e508.png" alt=""/>')
    newtext = newtext.replace('\ue509', '<img src="data/emoji/e509.png" alt=""/>')
    newtext = newtext.replace('\ue03b', '<img src="data/emoji/e03b.png" alt=""/>')

    newtext = newtext.replace('\ue04d', '<img src="data/emoji/e04d.png" alt=""/>')
    newtext = newtext.replace('\ue449', '<img src="data/emoji/e449.png" alt=""/>')
    newtext = newtext.replace('\ue44b', '<img src="data/emoji/e44b.png" alt=""/>')
    newtext = newtext.replace('\ue51d', '<img src="data/emoji/e51d.png" alt=""/>')
    newtext = newtext.replace('\ue44c', '<img src="data/emoji/e44c.png" alt=""/>')
    newtext = newtext.replace('\ue124', '<img src="data/emoji/e124.png" alt=""/>')
    newtext = newtext.replace('\ue121', '<img src="data/emoji/e121.png" alt=""/>')

    newtext = newtext.replace('\ue433', '<img src="data/emoji/e433.png" alt=""/>')
    newtext = newtext.replace('\ue202', '<img src="data/emoji/e202.png" alt=""/>')
    newtext = newtext.replace('\ue135', '<img src="data/emoji/e135.png" alt=""/>')
    newtext = newtext.replace('\ue01c', '<img src="data/emoji/e01c.png" alt=""/>')
    newtext = newtext.replace('\ue01d', '<img src="data/emoji/e01d.png" alt=""/>')
    newtext = newtext.replace('\ue10d', '<img src="data/emoji/e10d.png" alt=""/>')
    newtext = newtext.replace('\ue136', '<img src="data/emoji/e136.png" alt=""/>')

    newtext = newtext.replace('\ue42e', '<img src="data/emoji/e42e.png" alt=""/>')
    newtext = newtext.replace('\ue01b', '<img src="data/emoji/e01b.png" alt=""/>')
    newtext = newtext.replace('\ue15a', '<img src="data/emoji/e15a.png" alt=""/>')
    newtext = newtext.replace('\ue159', '<img src="data/emoji/e159.png" alt=""/>')
    newtext = newtext.replace('\ue432', '<img src="data/emoji/e432.png" alt=""/>')
    newtext = newtext.replace('\ue430', '<img src="data/emoji/e430.png" alt=""/>')
    newtext = newtext.replace('\ue431', '<img src="data/emoji/e431.png" alt=""/>')

    newtext = newtext.replace('\ue42f', '<img src="data/emoji/e42f.png" alt=""/>')
    newtext = newtext.replace('\ue01e', '<img src="data/emoji/e01e.png" alt=""/>')
    newtext = newtext.replace('\ue039', '<img src="data/emoji/e039.png" alt=""/>')
    newtext = newtext.replace('\ue435', '<img src="data/emoji/e435.png" alt=""/>')
    newtext = newtext.replace('\ue01f', '<img src="data/emoji/e01f.png" alt=""/>')
    newtext = newtext.replace('\ue125', '<img src="data/emoji/e125.png" alt=""/>')
    newtext = newtext.replace('\ue03a', '<img src="data/emoji/e03a.png" alt=""/>')

    newtext = newtext.replace('\ue14e', '<img src="data/emoji/e14e.png" alt=""/>')
    newtext = newtext.replace('\ue252', '<img src="data/emoji/e252.png" alt=""/>')
    newtext = newtext.replace('\ue137', '<img src="data/emoji/e137.png" alt=""/>')
    newtext = newtext.replace('\ue209', '<img src="data/emoji/e209.png" alt=""/>')
    newtext = newtext.replace('\ue154', '<img src="data/emoji/e154.png" alt=""/>')
    newtext = newtext.replace('\ue133', '<img src="data/emoji/e133.png" alt=""/>')
    newtext = newtext.replace('\ue150', '<img src="data/emoji/e150.png" alt=""/>')

    newtext = newtext.replace('\ue320', '<img src="data/emoji/e320.png" alt=""/>')
    newtext = newtext.replace('\ue123', '<img src="data/emoji/e123.png" alt=""/>')
    newtext = newtext.replace('\ue132', '<img src="data/emoji/e132.png" alt=""/>')
    newtext = newtext.replace('\ue143', '<img src="data/emoji/e143.png" alt=""/>')
    newtext = newtext.replace('\ue50b', '<img src="data/emoji/e50b.png" alt=""/>')
    newtext = newtext.replace('\ue514', '<img src="data/emoji/e514.png" alt=""/>')
    newtext = newtext.replace('\ue513', '<img src="data/emoji/e513.png" alt=""/>')

    newtext = newtext.replace('\ue50c', '<img src="data/emoji/e50c.png" alt=""/>')
    newtext = newtext.replace('\ue50d', '<img src="data/emoji/e50d.png" alt=""/>')
    newtext = newtext.replace('\ue511', '<img src="data/emoji/e511.png" alt=""/>')
    newtext = newtext.replace('\ue50f', '<img src="data/emoji/e50f.png" alt=""/>')
    newtext = newtext.replace('\ue512', '<img src="data/emoji/e512.png" alt=""/>')
    newtext = newtext.replace('\ue510', '<img src="data/emoji/e510.png" alt=""/>')
    newtext = newtext.replace('\ue50e', '<img src="data/emoji/e50e.png" alt=""/>')

    newtext = newtext.replace('\ue21c', '<img src="data/emoji/e21c.png" alt=""/>')
    newtext = newtext.replace('\ue21d', '<img src="data/emoji/e21d.png" alt=""/>')
    newtext = newtext.replace('\ue21e', '<img src="data/emoji/e21e.png" alt=""/>')
    newtext = newtext.replace('\ue21f', '<img src="data/emoji/e21f.png" alt=""/>')
    newtext = newtext.replace('\ue220', '<img src="data/emoji/e220.png" alt=""/>')
    newtext = newtext.replace('\ue221', '<img src="data/emoji/e221.png" alt=""/>')
    newtext = newtext.replace('\ue222', '<img src="data/emoji/e222.png" alt=""/>')

    newtext = newtext.replace('\ue223', '<img src="data/emoji/e223.png" alt=""/>')
    newtext = newtext.replace('\ue224', '<img src="data/emoji/e224.png" alt=""/>')
    newtext = newtext.replace('\ue225', '<img src="data/emoji/e225.png" alt=""/>')
    newtext = newtext.replace('\ue210', '<img src="data/emoji/e210.png" alt=""/>')
    newtext = newtext.replace('\ue232', '<img src="data/emoji/e232.png" alt=""/>')
    newtext = newtext.replace('\ue233', '<img src="data/emoji/e233.png" alt=""/>')
    newtext = newtext.replace('\ue235', '<img src="data/emoji/e235.png" alt=""/>')

    newtext = newtext.replace('\ue234', '<img src="data/emoji/e234.png" alt=""/>')
    newtext = newtext.replace('\ue236', '<img src="data/emoji/e236.png" alt=""/>')
    newtext = newtext.replace('\ue237', '<img src="data/emoji/e237.png" alt=""/>')
    newtext = newtext.replace('\ue238', '<img src="data/emoji/e238.png" alt=""/>')
    newtext = newtext.replace('\ue239', '<img src="data/emoji/e239.png" alt=""/>')
    newtext = newtext.replace('\ue23b', '<img src="data/emoji/e23b.png" alt=""/>')
    newtext = newtext.replace('\ue23a', '<img src="data/emoji/e23a.png" alt=""/>')

    newtext = newtext.replace('\ue23d', '<img src="data/emoji/e23d.png" alt=""/>')
    newtext = newtext.replace('\ue23c', '<img src="data/emoji/e23c.png" alt=""/>')
    newtext = newtext.replace('\ue24d', '<img src="data/emoji/e24d.png" alt=""/>')
    newtext = newtext.replace('\ue212', '<img src="data/emoji/e212.png" alt=""/>')
    newtext = newtext.replace('\ue24c', '<img src="data/emoji/e24c.png" alt=""/>')
    newtext = newtext.replace('\ue213', '<img src="data/emoji/e213.png" alt=""/>')
    newtext = newtext.replace('\ue214', '<img src="data/emoji/e214.png" alt=""/>')

    newtext = newtext.replace('\ue507', '<img src="data/emoji/e507.png" alt=""/>')
    newtext = newtext.replace('\ue203', '<img src="data/emoji/e203.png" alt=""/>')
    newtext = newtext.replace('\ue20b', '<img src="data/emoji/e20b.png" alt=""/>')
    newtext = newtext.replace('\ue22a', '<img src="data/emoji/e22a.png" alt=""/>')
    newtext = newtext.replace('\ue22b', '<img src="data/emoji/e22b.png" alt=""/>')
    newtext = newtext.replace('\ue226', '<img src="data/emoji/e226.png" alt=""/>')
    newtext = newtext.replace('\ue227', '<img src="data/emoji/e227.png" alt=""/>')

    newtext = newtext.replace('\ue22c', '<img src="data/emoji/e22c.png" alt=""/>')
    newtext = newtext.replace('\ue22d', '<img src="data/emoji/e22d.png" alt=""/>')
    newtext = newtext.replace('\ue215', '<img src="data/emoji/e215.png" alt=""/>')
    newtext = newtext.replace('\ue216', '<img src="data/emoji/e216.png" alt=""/>')
    newtext = newtext.replace('\ue217', '<img src="data/emoji/e217.png" alt=""/>')
    newtext = newtext.replace('\ue218', '<img src="data/emoji/e218.png" alt=""/>')
    newtext = newtext.replace('\ue228', '<img src="data/emoji/e228.png" alt=""/>')

    newtext = newtext.replace('\ue151', '<img src="data/emoji/e151.png" alt=""/>')
    newtext = newtext.replace('\ue138', '<img src="data/emoji/e138.png" alt=""/>')
    newtext = newtext.replace('\ue139', '<img src="data/emoji/e139.png" alt=""/>')
    newtext = newtext.replace('\ue13a', '<img src="data/emoji/e13a.png" alt=""/>')
    newtext = newtext.replace('\ue208', '<img src="data/emoji/e208.png" alt=""/>')
    newtext = newtext.replace('\ue14f', '<img src="data/emoji/e14f.png" alt=""/>')
    newtext = newtext.replace('\ue20a', '<img src="data/emoji/e20a.png" alt=""/>')

    newtext = newtext.replace('\ue434', '<img src="data/emoji/e434.png" alt=""/>')
    newtext = newtext.replace('\ue309', '<img src="data/emoji/e309.png" alt=""/>')
    newtext = newtext.replace('\ue315', '<img src="data/emoji/e315.png" alt=""/>')
    newtext = newtext.replace('\ue30d', '<img src="data/emoji/e30d.png" alt=""/>')
    newtext = newtext.replace('\ue207', '<img src="data/emoji/e207.png" alt=""/>')
    newtext = newtext.replace('\ue229', '<img src="data/emoji/e229.png" alt=""/>')
    newtext = newtext.replace('\ue206', '<img src="data/emoji/e206.png" alt=""/>')

    newtext = newtext.replace('\ue205', '<img src="data/emoji/e205.png" alt=""/>')
    newtext = newtext.replace('\ue204', '<img src="data/emoji/e204.png" alt=""/>')
    newtext = newtext.replace('\ue12e', '<img src="data/emoji/e12e.png" alt=""/>')
    newtext = newtext.replace('\ue250', '<img src="data/emoji/e250.png" alt=""/>')
    newtext = newtext.replace('\ue251', '<img src="data/emoji/e251.png" alt=""/>')
    newtext = newtext.replace('\ue14a', '<img src="data/emoji/e14a.png" alt=""/>')
    newtext = newtext.replace('\ue149', '<img src="data/emoji/e149.png" alt=""/>')

    newtext = newtext.replace('\ue23f', '<img src="data/emoji/e23f.png" alt=""/>')
    newtext = newtext.replace('\ue240', '<img src="data/emoji/e240.png" alt=""/>')
    newtext = newtext.replace('\ue241', '<img src="data/emoji/e241.png" alt=""/>')
    newtext = newtext.replace('\ue242', '<img src="data/emoji/e242.png" alt=""/>')
    newtext = newtext.replace('\ue243', '<img src="data/emoji/e243.png" alt=""/>')
    newtext = newtext.replace('\ue244', '<img src="data/emoji/e244.png" alt=""/>')
    newtext = newtext.replace('\ue245', '<img src="data/emoji/e245.png" alt=""/>')

    newtext = newtext.replace('\ue246', '<img src="data/emoji/e246.png" alt=""/>')
    newtext = newtext.replace('\ue247', '<img src="data/emoji/e247.png" alt=""/>')
    newtext = newtext.replace('\ue248', '<img src="data/emoji/e248.png" alt=""/>')
    newtext = newtext.replace('\ue249', '<img src="data/emoji/e249.png" alt=""/>')
    newtext = newtext.replace('\ue24a', '<img src="data/emoji/e24a.png" alt=""/>')
    newtext = newtext.replace('\ue24b', '<img src="data/emoji/e24b.png" alt=""/>')
    newtext = newtext.replace('\ue23e', '<img src="data/emoji/e23e.png" alt=""/>')

    newtext = newtext.replace('\ue532', '<img src="data/emoji/e532.png" alt=""/>')
    newtext = newtext.replace('\ue533', '<img src="data/emoji/e533.png" alt=""/>')
    newtext = newtext.replace('\ue534', '<img src="data/emoji/e534.png" alt=""/>')
    newtext = newtext.replace('\ue535', '<img src="data/emoji/e535.png" alt=""/>')
    newtext = newtext.replace('\ue21a', '<img src="data/emoji/e21a.png" alt=""/>')
    newtext = newtext.replace('\ue219', '<img src="data/emoji/e219.png" alt=""/>')
    newtext = newtext.replace('\ue21b', '<img src="data/emoji/e21b.png" alt=""/>')

    newtext = newtext.replace('\ue02f', '<img src="data/emoji/e02f.png" alt=""/>')
    newtext = newtext.replace('\ue024', '<img src="data/emoji/e024.png" alt=""/>')
    newtext = newtext.replace('\ue025', '<img src="data/emoji/e025.png" alt=""/>')
    newtext = newtext.replace('\ue026', '<img src="data/emoji/e026.png" alt=""/>')
    newtext = newtext.replace('\ue027', '<img src="data/emoji/e027.png" alt=""/>')
    newtext = newtext.replace('\ue028', '<img src="data/emoji/e028.png" alt=""/>')
    newtext = newtext.replace('\ue029', '<img src="data/emoji/e029.png" alt=""/>')

    newtext = newtext.replace('\ue02a', '<img src="data/emoji/e02a.png" alt=""/>')
    newtext = newtext.replace('\ue02b', '<img src="data/emoji/e02b.png" alt=""/>')
    newtext = newtext.replace('\ue02c', '<img src="data/emoji/e02c.png" alt=""/>')
    newtext = newtext.replace('\ue02d', '<img src="data/emoji/e02d.png" alt=""/>')
    newtext = newtext.replace('\ue02e', '<img src="data/emoji/e02e.png" alt=""/>')
    newtext = newtext.replace('\ue332', '<img src="data/emoji/e332.png" alt=""/>')
    newtext = newtext.replace('\ue333', '<img src="data/emoji/e333.png" alt=""/>')

    newtext = newtext.replace('\ue24e', '<img src="data/emoji/e24e.png" alt=""/>')
    newtext = newtext.replace('\ue24f', '<img src="data/emoji/e24f.png" alt=""/>')
    newtext = newtext.replace('\ue537', '<img src="data/emoji/e537.png" alt=""/>')

    return newtext

def convertsmileys (text):
    global PYTHON_VERSION
    if PYTHON_VERSION == 2:
        newtext = convert_smileys_python_2.convertsmileys_python2 (text)
    elif PYTHON_VERSION == 3:
        newtext = convertsmileys_python3 (text)
    return newtext

################################################################################
# def groupinfo

def GroupInfo (Cid):
    GroupAdmin = None
    GroupCreationTime = None

    if '@g.us' in Cid:
        Group = Cid.split("@")[0]
        GroupAdmin, GroupCreationTimeStamp = Group.split("-")
        #GroupCreationTime = str(datetime.datetime.fromtimestamp(int(GroupCreationTimeStamp)))[:10]
        GroupCreationTime = str(datetime.datetime.fromtimestamp(int(GroupCreationTimeStamp)))
    return GroupAdmin, GroupCreationTime

################################################################################
#Functions for Find Offline File
# https://stackoverflow.com/questions/24828383/how-to-read-the-thumb-image-column-in-the-whatsapp-messengers-sqlite3-database
# https://stackoverflow.com/questions/2186525/use-a-glob-to-find-files-recursively-in-python

def filelistonce (folder, date):
    flistnames = []
    flistsizes = []
    for root, dirnames, filenames in os.walk(folder):
        for filename in fnmatch.filter(filenames, '*'+date+'*'):
            #print("root:" + root + " filename:" + filename)
            flistnames.append(os.path.join(root, filename))
            statinfo = os.stat(os.path.join(root, filename))
            fsize = statinfo.st_size
            flistsizes.append(fsize)

    flist = [flistnames, flistsizes]
    return flist

def filelist (type, date):
    folder = None
    folder2 = None
    flist = None
    if type == 'IMG':
        folder =  'Media/WhatsApp Images/'
        if not date in flistimg:
            flistimg[date] = filelistonce (folder, date)
        flist = flistimg[date]
    elif type == 'AUD':
        folder =  'Media/WhatsApp Audio/'
        if not date in flistaud:
            flistaud[date] = filelistonce (folder, date)
        flist = flistaud[date]
    elif type == 'VID':
        folder = 'Media/WhatsApp Video/'
        if not date in flistvid:
            flistvid[date] = filelistonce (folder, date)
        flist = flistvid[date]
    elif type == 'PTT':
        folder = 'Media/WhatsApp Voice Notes/'
        if not date in flistptt:
            flistptt[date] = filelistonce (folder, date)
        flist = flistptt[date]
    elif type == 'DOC':
        folder = 'Media/WhatsApp Documents/'
        if not date in flistdoc:
            flistdoc[date] = filelistonce (folder, date)
        flist = flistdoc[date]
    elif type == 'GIF':
        folder = 'Media/WhatsApp Animated Gifs/'
        if not date in flistgif:
            flistgif[date] = filelistonce (folder, date)
        flist = flistgif[date]
    return folder, flist

def findfile (type, size, localurl, date, additionaldays):
    fname = ''
    try:
        if mode == ANDROID:
            date = str(date)
            z = 0
            while fname == '':
                z = z + 1
                #use or create list of all media files of that type and that date
                folder, flist = filelist (type, date)
                #search the file with the given size
                try:
                    fname = flist [0] [ flist[1].index(size) ]
                except:
                    fname = ''          
                if fname == '':
                    if z >= 1 + additionaldays:
                        #if file is not found for "today", then try for "tomorrow" and "the day after tomorrow". If it's still not found, then try to find the temporary file, if not successful then just link the media folder
                        if os.path.exists(folder+localurl):
                            fname = folder+localurl
                        else:
                            fname = folder
                    else:
                        timestamptoday = int(str(time.mktime(datetime.datetime.strptime(date, "%Y%m%d").timetuple()))[:-2])
                        timestamptomorrow = timestamptoday + 86400
                        tomorrow = str(datetime.datetime.fromtimestamp(timestamptomorrow))[:10]
                        tomorrow = tomorrow.replace("-","")
                        date = tomorrow
        elif mode == IPHONE:
            #folder = 'Media/'
            #if os.path.exists(localurl):
            #    fname = localurl
            #else:
            #    fname = folder
            fname = localurl
    except:
        print ("error while searching for files type " + type + " in localurl " + localurl + " at date " + date)
    #return the file name
    return fname

################################################################################
# Functions for opening and closing of output files

# Receives the name of an output file to create and initialize, and also a
# DB owner name
def outputfile_open(file_name, db_owner):

    file_object = None;

    file_object = open(file_name,'wb')

    print("Creating file " + file_name + "...")
    # writes page header
    file_object.write('<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.01 Transitional//EN"\n'.encode('utf-8'))
    file_object.write('"http://www.w3.org/TR/html4/loose.dtd">\n'.encode('utf-8'))
    file_object.write('<html><head><title>{0}</title>\n'.format(file_name).encode('utf-8'))
    file_object.write('<meta http-equiv="Content-Type" content="text/html; charset=UTF-8"/>\n'.encode('utf-8'))
    # adds page style
    file_object.write(css_style.encode('utf-8'))

    # adds javascript to make the tables sortable
    file_object.write('\n<script type="text/javascript">\n'.encode('utf-8'))
    file_object.write(popups.encode('utf-8'))
    file_object.write(sortable.encode('utf-8'))
    file_object.write('</script>\n\n'.encode('utf-8'))
    file_object.write('</head><body>\n'.encode('utf-8'))

    # H1 Title
    #file_object.write('<h1>Zena Forensics<h1>'.encode('utf-8'))
    file_object.write('<h1>WhatsApp Xtract 2.3.1</h1>'.encode('utf-8'))

    # H2 DB Owner
    file_object.write('<a name="top"></a><h3>'.encode('utf-8'))

    if mode == IPHONE:
        file_object.write(' [APPLE] '.encode('utf-8'))
    elif mode == ANDROID:
        file_object.write(' [ANDROID] '.encode('utf-8'))
    file_object.write(' {0}</h3>\n'.format(db_owner).encode('utf-8'))

    return file_object;

def outputfile_close(file_object):

    # writes page footer
    file_object.write('</body></html>\n'.encode('utf-8'))
    file_object.close()

    return;

################################################################################
################################################################################
# MAIN
def main(argv):

    chat_session_list = []
    global mode
    global PYTHON_VERSION

    # parser options
    parser = ArgumentParser(description='Converts a Whatsapp database to HTML.')
    parser.add_argument(dest='infile', 
                       help="input 'msgstore.db' or 'msgstore.db.crypt' (Android) or 'ChatStorage.sqlite' (iPhone) file to scan")
    parser.add_argument('-w', '--wafile', dest='wafile', 
                       help="optionally input 'wa.db' (Android) file to scan")
    parser.add_argument('-o', '--outfile',  dest='outfile', 
                       help="optionally choose name of output file")
    options = parser.parse_args()

    # checks for the wadb file
    if options.wafile is None:
        have_wa = False
    elif not os.path.exists(options.wafile):
        print('"{}" file is not found!'.format(options.wafile))
        sys.exit(1)
    else:
        have_wa = True

    # checks for the input file
    if options.infile is None:
        parser.print_help()
        sys.exit(1)
    if not os.path.exists(options.infile):
        print('"{}" file is not found!'.format(options.infile))
        sys.exit(1)

    # connects to the database(s)
    msgstore = sqlite3.connect(options.infile)
    msgstore.row_factory = sqlite3.Row
    c1 = msgstore.cursor()
    c2 = msgstore.cursor()
    
    # check on platform
    try:
        c1.execute("SELECT * FROM ZWACHATSESSION")
        # if succeeded --> IPHONE mode
        mode = IPHONE
        print ("iPhone mode!\n")
    except:
        # if failed --> ANDROID mode
        mode = ANDROID
        print ("Android mode!\n")
   
    if mode == ANDROID:
        if have_wa:
            wastore = sqlite3.connect(options.wafile)
            wastore.row_factory = sqlite3.Row
            wa = wastore.cursor()
        # check if crypted and decrypt
        repairedfile = ""
        decodedfile = ""
        try:
            c1.execute("SELECT * FROM chat_list")
        except sqlite3.Error as msg:
            try:
                print ("trying to repair android database...")
                c1.close()
                c2.close()
                msgstore.close()
                repairedfile = options.infile + "_repaired.db"
                if os.path.exists(repairedfile):
                    os.remove(repairedfile)
                os.system('echo .dump | sqlite3 "%s" > Temp.sql' % options.infile)
                os.system('echo .quit | sqlite3 -init Temp.sql "%s"' % repairedfile)
                if os.path.exists("Temp.sql"):
                    os.remove("Temp.sql")
                msgstore = sqlite3.connect(repairedfile)
                msgstore.row_factory = sqlite3.Row
                c1 = msgstore.cursor()          
                c2 = msgstore.cursor() 
                c1.execute("SELECT * FROM chat_list")
            except sqlite3.Error as msg:             
                try:
                    print ("trying to decrypt android database...")
                    c1.close()
                    c2.close()
                    msgstore.close()
                    if os.path.exists(repairedfile):
                        os.remove(repairedfile) 
                    from Crypto.Cipher import AES
                    code = "346a23652a46392b4d73257c67317e352e3372482177652c"
                    if PYTHON_VERSION == 2:
                        code = code.decode('hex')
                    elif PYTHON_VERSION == 3:
                        code = bytes.fromhex(code)
                    cipher = AES.new(code,1)
                    decoded = cipher.decrypt(open(options.infile,"rb").read())
                    decodedfile = options.infile.replace(".db.crypt","")+".plain.db"
                    output = open(decodedfile,"wb")
                    output.write(decoded)
                    output.close()
                    #print ("size:" + str(len (decoded)) )
                    msgstore = sqlite3.connect(decodedfile)
                    msgstore.row_factory = sqlite3.Row
                    c1 = msgstore.cursor()          
                    c2 = msgstore.cursor()   
                    print ("decrypted database written to "+decodedfile)
                    c1.execute("SELECT * FROM chat_list")
                except sqlite3.Error as msg:
                    try:
                        if os.path.exists(decodedfile):
                            print ("trying to repair decrypted android database...")
                            c1.close()
                            c2.close()
                            msgstore.close()
                            repairedfile = decodedfile + "_repaired.db"
                            if os.path.exists(repairedfile):
                                os.remove(repairedfile)
                            os.system('echo .dump | sqlite3 "%s" > Temp.sql' % decodedfile)
                            os.system('echo .quit | sqlite3 -init Temp.sql "%s"' % repairedfile)
                            if os.path.exists("Temp.sql"):
                                os.remove("Temp.sql")
                            msgstore = sqlite3.connect(repairedfile)
                            msgstore.row_factory = sqlite3.Row
                            c1 = msgstore.cursor()          
                            c2 = msgstore.cursor() 
                            c1.execute("SELECT * FROM chat_list")
                    except sqlite3.Error as msg:
                        print("Could not open database file. Guess it's not a valid Android or Iphone database file. ")
                        try:
                            c1.close()
                            c2.close()
                            msgstore.close()
                            if os.path.exists(repairedfile):
                                os.remove(repairedfile)
                            #if os.path.exists(decodedfile):
                            #    os.remove(decodedfile)
                        except:
                            print('Could not clean up.')
                        sys.exit(1)
                except ValueError as msg:
                    print('Error during decrypting: {}'.format(msg))
                    print("Could not decrypt database file. Guess it's not a valid Android/Iphone database file or Whatsapp changed the encryption.")
                    sys.exit(1)
                          
    # gets metadata plist info (iphone only)
    if mode == IPHONE:            
        try:
            # ------------------------------------------------------ #
            #  IPHONE  ChatStorage.sqlite file *** Z_METADATA TABLE  #
            # ------------------------------------------------------ #
            # Z_VERSION INTEGER PRIMARY KEY
            # Z_UIID VARCHAR
            # Z_PLIST BLOB
            from bplist import BPlistReader
            c1.execute("SELECT * FROM Z_METADATA")
            metadata = c1.fetchone()
            print ("*** METADATA PLIST DUMP ***\n")
            print ("Plist ver.:  {}".format(metadata["Z_VERSION"]))
            print ("UUID:        {}".format(metadata["Z_UUID"]))
            bpReader = BPlistReader(metadata["Z_PLIST"])
            plist = bpReader.parse()

            for entry in plist.items():
                if entry[0] == "NSStoreModelVersionHashes":
                    print ("{}:".format(entry[0]))
                    for inner_entry in entry[1].items():
                        print ("\t{}: {}".format(inner_entry[0],base64.b64encode(inner_entry[1]).decode("utf-8")))
                else:
                    print ("{}: {}".format(entry[0],entry[1]))
            print ("\n***************************\n")
            
        except:
            print ("Metadata Plist Dump is failed. Note that you need to use Python 2.7 for that bplist.py works")

    # gets all the chat sessions
    try:
        if mode == ANDROID:
            if have_wa:
                wa.execute("SELECT * FROM wa_contacts WHERE is_whatsapp_user = 1 GROUP BY jid")
                for chats in wa:
                    # ------------------------------------------ #
                    #  ANDROID WA.db file *** wa_contacts TABLE  #
                    # ------------------------------------------ #
                    # chats[0] --> _id (primary key)
                    # chats[1] --> jid
                    # chats[2] --> is_whatsapp_user
                    # chats[3] --> is_iphone
                    # chats[4] --> status
                    # chats[5] --> number
                    # chats[6] --> raw_contact_id
                    # chats[7] --> display_name
                    # chats[8] --> phone_type
                    # chats[9] --> phone_label
                    # chats[10] -> unseen_msg_count
                    # chats[11] -> photo_ts
                    try:
                        c2.execute("SELECT message_table_id FROM chat_list WHERE key_remote_jid=?", [chats["jid"]])
                        lastmessage = c2.fetchone()[0]
                        #!todo alternativ maximale _id WHERE key_remote_jid 
                        c2.execute("SELECT timestamp FROM messages WHERE _id=?", [lastmessage])
                        lastmessagedate = c2.fetchone()[0]
                    except: #not all contacts that are whatsapp users may already have been chatted with
                        lastmessagedate = None
                    curr_chat = Chatsession(chats["_id"],chats["display_name"],chats["jid"],None,chats["unseen_msg_count"],chats["status"],lastmessagedate)
                    chat_session_list.append(curr_chat)
            else:
                c1.execute("SELECT * FROM chat_list")
                for chats in c1:
                    # ---------------------------------------------- #
                    #  ANDROID MSGSTORE.db file *** chat_list TABLE  #
                    # ---------------------------------------------- #
                    # chats[0] --> _id (primary key)
                    # chats[1] --> key_remote_jid (contact jid or group chat jid)
                    # chats[2] --> message_table_id (id of last message in this chat, corresponds to table messages primary key)
                    name = chats["key_remote_jid"].split('@')[0]
                    try:
                        lastmessage = chats["message_table_id"] 
                        c2.execute("SELECT timestamp FROM messages WHERE _id=?", [lastmessage])
                        lastmessagedate = c2.fetchone()[0]
                    except:
                        lastmessagedate = None
                    curr_chat = Chatsession(chats["_id"],name,chats["key_remote_jid"],None,None,None,lastmessagedate)
                    chat_session_list.append(curr_chat)  
            #now retrieve thumbnail database
            try:
                thumbsDict = {}
                c2.execute("SELECT key_id, thumbnail FROM message_thumbnails")
                for row in c2:
                    thumbsDict[row["key_id"]]=row["thumbnail"]
            except:
                thumbs = None
                sys.exit()
        elif mode == IPHONE:
            c1.execute("SELECT * FROM ZWACHATSESSION")
            for chats in c1:
                # ---------------------------------------------------------- #
                #  IPHONE  ChatStorage.sqlite file *** ZWACHATSESSION TABLE  #
                # ---------------------------------------------------------- #
                # chats[0] --> Z_PK (primary key)
                # chats[1] --> Z_ENT
                # chats[2] --> Z_OPT
                # chats[3] --> ZINCLUDEUSERNAME
                # chats[4] --> ZUNREADCOUNT
                # chats[5] --> ZCONTACTABID
                # chats[6] --> ZMESSAGECOUNTER
                # chats[7] --> ZLASTMESSAGEDATE
                # chats[8] --> ZCONTACTJID
                # chats[9] --> ZSAVEDINPUT
                # chats[10] -> ZPARTNERNAME
                # chats[11] -> ZLASTMESSAGETEXT

                try:
                    c2.execute("SELECT ZSTATUSTEXT FROM ZWASTATUS WHERE ZCONTACTABID =?;", [chats["ZCONTACTABID"]])
                    statustext = c2.fetchone()[0]
                except:
                    statustext = None
                # ---------------------------------------------------------- #
                #  IPHONE  ChatStorage.sqlite file *** ZWASTATUS TABLE       #
                # ---------------------------------------------------------- #
                # Z_PK (primary key)
                # Z_ENT
                # Z_OPT
                # ZEXPIRATIONTIME
                # ZCONTACTABID
                # ZNOPUSH
                # ZFAVORITE
                # ZSTATUSDATE
                # ZPHONENUMBER
                # c2.fetchone()[0] --> ZSTATUSTEXT
                # ZWHATSAPPID
                curr_chat = Chatsession(chats["Z_PK"],chats["ZPARTNERNAME"],chats["ZCONTACTJID"],chats["ZMESSAGECOUNTER"],chats["ZUNREADCOUNT"],statustext,chats["ZLASTMESSAGEDATE"])
                chat_session_list.append(curr_chat)
        chat_session_list = sorted(chat_session_list, key=lambda Chatsession: Chatsession.last_message_date, reverse=True)
                

    except sqlite3.Error as msg:
        print('Error: {}'.format(msg))
        sys.exit(1)

    # for each chat session, gets all messages
    count_chats = 0
    for chats in chat_session_list:
        count_chats = count_chats + 1
        try:
            if mode == ANDROID:
                c1.execute("SELECT * FROM messages WHERE key_remote_jid=? ORDER BY _id ASC;", [chats.contact_id])
            elif mode == IPHONE:
                c1.execute("SELECT * FROM ZWAMESSAGE WHERE ZCHATSESSION=? ORDER BY Z_PK ASC;", [chats.pk_cs])
            count_messages = 0
            for msgs in c1:
                count_messages = count_messages + 1
                try:
                    if mode == ANDROID:
                        # --------------------------------------------- #
                        #  ANDROID MSGSTORE.db file *** messages TABLE  #
                        # --------------------------------------------- #
                        # msgs[0] --> _id (primary key)
                        # msgs[1] --> key_remote_jid
                        # msgs[2] --> key_from_me
                        # msgs[3] --> key_id
                        # msgs[4] --> status
                        # msgs[5] --> needs_push
                        # msgs[6] --> data
                        # msgs[7] --> timestamp
                        # msgs[8] --> media_url
                        # msgs[9] --> media_mime_type
                        # msgs[10] -> media_wa_type
                        # msgs[11] -> media_size
                        # msgs[12] -> media_name
                        # msgs[13] -> media_duration
                        # msgs[14] -> latitude
                        # msgs[15] -> longitude
                        # msgs[16] -> thumb_image
                        # msgs[17] -> remote_resource
                        # msgs[18] -> received_timestamp
                        # msgs[19] -> send_timestamp
                        # msgs[20] -> receipt_server_timestamp
                        # msgs[21] -> receipt_device_timestamp
                        # message sender
                        if msgs["remote_resource"] == "" or msgs["remote_resource"] is None:
                            contactfrom = msgs["key_remote_jid"]
                        else:
                            contactfrom = msgs["remote_resource"]
                        if msgs["key_from_me"] == 1:
                            contactfrom = "me"
                        thumbnaildata = None
                        if msgs["raw_data"] is not None:
                            try:
                                thumbnaildata = msgs["raw_data"]
                            except:
                                thumbnaildata = None
                        elif msgs["thumb_image"] is not None:
                            try:
                                thumbnaildata=thumbsDict[msgs["key_id"]]
                            except:
                                thumbnaildata = None
                        try:
                            mduration =  msgs["media_duration"]
                        except:
                            mduration = None
                        curr_message = Message(msgs["_id"],msgs["key_from_me"],msgs["key_id"],msgs["timestamp"],msgs["data"],contactfrom,msgs["status"],msgs["media_name"],msgs["media_url"],thumbnaildata,None,msgs["media_wa_type"],msgs["media_size"],mduration,msgs["latitude"],msgs["longitude"],None,None)
                    elif mode == IPHONE:
                        #  IPHONE ChatStorage.sqlite file *** ZWACHATSESSION TABLE  #
                        # ------------------------------------------------------- #
                        # ------------------------------------------------------- #
                        # msgs[0] --> Z_PK (primary key)
                        # msgs[1] --> Z_ENT
                        # msgs[2] --> Z_OPT
                        # msgs[3] --> ZISFROMME
                        # msgs[4] --> ZSORT
                        # msgs[5] --> ZMESSAGESTATUS
                        # msgs[6] --> ZMESSAGETYPE
                        # msgs[7] --> ZMEDIAITEM
                        # msgs[8] --> ZCHATSESSION
                        # msgs[9] --> ZMESSAGEDATE
                        # msgs[10] -> ZTEXT
                        # msgs[11] -> ZTOJID
                        # msgs[12] -> ZFROMJID
                        # msgs[13] -> ZSTANZAID
                        if msgs["ZISFROMME"] == 1:
                            contactfrom = "me"
                        else:
                            contactfrom = msgs["ZFROMJID"]
                        if msgs["ZMEDIAITEM"] is None:
                            curr_message = Message(msgs["Z_PK"],msgs["ZISFROMME"],None,msgs["ZMESSAGEDATE"],msgs["ZTEXT"],contactfrom,msgs["ZMESSAGESTATUS"],None,None,None,None,None,None,None,None,None,None,None)
                        else:
                            try:
                                messagetext = str(msgs["ZTEXT"])
                            except:
                                messagetext = ""
                            try:
                                c2.execute("SELECT * FROM ZWAMEDIAITEM WHERE Z_PK=?;", [msgs["ZMEDIAITEM"]])
                                media = c2.fetchone()
                                # ------------------------------------------------------- #
                                #  IPHONE ChatStorage.sqlite file *** ZWAMEDIAITEM TABLE  #
                                # ------------------------------------------------------- #
                                # Z_PK INTEGER PRIMARY KEY
                                # Z_ENT INTEGER
                                # Z_OPT INTEGER
                                # ZMOVIEDURATION INTEGER
                                # ZMEDIASAVED INTEGER
                                # ZFILESIZE INTEGER
                                # ZMESSAGE INTEGER
                                # ZLONGITUDE FLOAT
                                # ZHACCURACY FLOAT
                                # ZLATITUDE FLOAT
                                # ZVCARDSTRING VARCHAR
                                # ZXMPPTHUMBPATH VARCHAR
                                # ZMEDIALOCALPATH VARCHAR
                                # ZMEDIAURL VARCHAR
                                # ZVCARDNAME VARCHAR
                                # ZTHUMBNAILLOCALPATH VARCHAR
                                # ZTHUMBNAILDATA BLOB
                                try:
                                    movieduration = media["ZMOVIEDURATION"]
                                except:
                                    movieduration = 0
                                if movieduration > 0:
                                    mediawatype = "3"
                                else:
                                    mediawatype = msgs["ZMESSAGETYPE"]
                                try:
                                    ZXMPPTHUMBPATH = media["ZXMPPTHUMBPATH"]
                                except:
                                    ZXMPPTHUMBPATH = None
                                curr_message = Message(msgs["Z_PK"],msgs["ZISFROMME"],None,msgs["ZMESSAGEDATE"],msgs["ZTEXT"],contactfrom,msgs["ZMESSAGESTATUS"],media["ZMEDIALOCALPATH"],media["ZMEDIAURL"],media["ZTHUMBNAILDATA"],ZXMPPTHUMBPATH,mediawatype,media["ZFILESIZE"],None,media["ZLATITUDE"],media["ZLONGITUDE"],media["ZVCARDNAME"],media["ZVCARDSTRING"])
                            except TypeError as msg:
                                print('Error TypeError while reading media message #{} in chat #{}: {}'.format(count_messages, chats.pk_cs, msg) + "\nI guess this means that the media part of this message can't be found in the DB") 
                                curr_message = Message(msgs["Z_PK"],msgs["ZISFROMME"],None,msgs["ZMESSAGEDATE"],messagetext + "<br>MediaMessage_Error: see output in DOS window",contactfrom,msgs["ZMESSAGESTATUS"],None,None,None,None,None,None,None,None,None,None,None)
                            except sqlite3.Error as msg:
                                print('Error sqlite3.Error while reading media message #{} in chat #{}: {}'.format(count_messages, chats.pk_cs, msg)) 
                                curr_message = Message(msgs["Z_PK"],msgs["ZISFROMME"],None,msgs["ZMESSAGEDATE"],messagetext + "<br>MediaMessage_Error: see output in DOS window",contactfrom,msgs["ZMESSAGESTATUS"],None,None,None,None,None,None,None,None,None,None,None)                                

                except sqlite3.Error as msg:
                    print('Error while reading message #{} in chat #{}: {}'.format(count_messages, chats.pk_cs, msg)) 
                    curr_message = Message(None,None,None,None,"_Error: sqlite3.Error, see output in DOS window",None,None,None,None,None,None,None,None,None,None,None,None,None)
                except TypeError as msg:
                    print('Error while reading message #{} in chat #{}: {}'.format(count_messages, chats.pk_cs, msg)) 
                    curr_message = Message(None,None,None,None,"_Error: TypeError, see output in DOS window",None,None,None,None,None,None,None,None,None,None,None,None,None)
                chats.msg_list.append(curr_message)
                
            chats.contact_msg_count = count_messages

        except sqlite3.Error as msg:
            print('Error sqlite3.Error while reading chat #{}: {}'.format(chats.pk_cs, msg)) 
            sys.exit(1)
        except TypeError as msg:
            print('Error TypeError while reading chat #{}: {}'.format(chats.pk_cs, msg)) 
            sys.exit(1)

    # gets the db owner id
    try:
        if mode == ANDROID:
            #c1.execute("SELECT key_remote_jid FROM messages WHERE key_from_me=1 AND key_remote_jid LIKE '%@s.whatsapp.net%' ")
            #doesn't work
            owner = ""
        elif mode == IPHONE:
            c1.execute("SELECT ZFROMJID FROM ZWAMESSAGE WHERE ZISFROMME=1")
        try:
            owner = (c1.fetchone()[0]).split('/')[0]
        except:
            owner = ""
    except sqlite3.Error as msg:
        print('Error: {}'.format(msg))

    # OUTPUT
    if options.outfile is None:
        outfile = owner
    else:
        outfile = options.outfile
    if owner == "":
        outfile = options.infile.replace(".crypt","")
    outfile = '%s.html' % outfile
    #wfile = open(outfile,'wb')
    main_file = outputfile_open(outfile, owner)
    print ("printing output to "+outfile+" ...")

    # writes 1st table header "CHAT SESSION"
    main_file.write('<table class="sortable" id="chatsession" border="1" cellpadding="2" cellspacing="0">\n'.encode('utf-8'))
    main_file.write('<thead>\n'.encode('utf-8'))
    main_file.write('<tr>\n'.encode('utf-8'))
    main_file.write('<th>PK</th>\n'.encode('utf-8'))
    main_file.write('<th>Contact Name</th>\n'.encode('utf-8'))
    main_file.write('<th>Contact ID</th>\n'.encode('utf-8'))
    main_file.write('<th>Status</th>\n'.encode('utf-8'))
    main_file.write('<th># Msg</th>\n'.encode('utf-8'))
    main_file.write('<th># Unread Msg</th>\n'.encode('utf-8'))
    main_file.write('<th>Last Message</th>\n'.encode('utf-8'))
    main_file.write('</tr>\n'.encode('utf-8'))
    main_file.write('</thead>\n'.encode('utf-8'))
    
    # writes 1st table content
    main_file.write('<tbody>\n'.encode('utf-8'))
    for i in chat_session_list:
    	
        if i.contact_msg_count == 0:
            continue;

        if i.contact_name == "N/A":
            try:
                i.contact_name = i.contact_id.split('@')[0]
            except:
                i.contact_name = i.contact_id
            contactname = i.contact_name
        else:
            contactname = convertsmileys ( i.contact_name ) # chat name
        contactstatus = convertsmileys ( str(i.contact_status) )
        lastmessagedate = i.last_message_date
        main_file.write('<tr>\n'.encode('utf-8'))
        main_file.write('<td>{}</td>\n'.format(i.pk_cs).encode('utf-8'))
        #main_file.write('<td class="contact"><a href="#{}">{}</a></td>\n'.format(i.contact_name,contactname).encode('utf-8'))
        main_file.write('<td class="contact"><a href="{0}.{1}.html">{2}</a></td>\n'.format(outfile,i.contact_id.split('@')[0],contactname).encode('utf-8'))
        main_file.write('<td class="contact">{}</td>\n'.format(i.contact_id).encode('utf-8'))
        main_file.write('<td>{}</td>\n'.format(contactstatus).encode('utf-8'))
        main_file.write('<td>{}</td>\n'.format(i.contact_msg_count).encode('utf-8'))
        main_file.write('<td>{}</td>\n'.format(i.contact_unread_msg).encode('utf-8'))
        main_file.write('<td>{}</td>\n'.format(lastmessagedate).encode('utf-8'))
        main_file.write('</tr>\n'.encode('utf-8'))
    main_file.write('</tbody>\n'.encode('utf-8'))
    # writes 1st table footer
    main_file.write('</table>\n'.encode('utf-8'))

    # Close main file
    outputfile_close(main_file)

    global content_type

    # writes a table for each chat session
    for i in chat_session_list:#


        if i.contact_msg_count == 0:
            continue;

        chat_file = outputfile_open( '{0}.{1}.html'.format(outfile,i.contact_id.split('@')[0]), owner );


        contactname = convertsmileys ( i.contact_name ) # chat name
        try:
            chatid = i.contact_id.split('@')[0]
        except:
            chatid = i.contact_id
        
        chat_file.write('<h3><a href="{0}">Return to index</a></h3>'.format( outfile ).encode( 'utf-8' ) )
        
        # Group Information
        GAdmin, GCreationTime = GroupInfo(i.contact_id)
        if GAdmin is not None:
            chat_file.write('<h3>Group Creation-Time: {1} - Group Creator: {0}</h3>\n'.format(GAdmin, GCreationTime).encode('utf-8'))
        
        chat_file.write('<h3>Chat session #{}: <a name="{}">{}</a></h3>\n'.format(i.pk_cs, i.contact_name, contactname).encode('utf-8'))
        chat_file.write('<table class="sortable" id="msg_{}" border="1" cellpadding="2" cellspacing="0">\n'.format(chatid).encode('utf-8'))
        chat_file.write('<thead>\n'.encode('utf-8'))
        chat_file.write('<tr>\n'.encode('utf-8'))
        chat_file.write('<th>PK</th>\n'.encode('utf-8'))
        #chat_file.write('<th>Chat</th>\n'.encode('utf-8'))
        chat_file.write('<th>Msg date</th>\n'.encode('utf-8'))
        chat_file.write('<th>From</th>\n'.encode('utf-8'))
        chat_file.write('<th>Msg content</th>\n'.encode('utf-8'))
        chat_file.write('<th>Msg status</th>\n'.encode('utf-8'))
        chat_file.write('<th>Media Type</th>\n'.encode('utf-8'))
        chat_file.write('<th>Media Size</th>\n'.encode('utf-8'))
        chat_file.write('</tr>\n'.encode('utf-8'))
        chat_file.write('</thead>\n'.encode('utf-8'))

        # writes table content
        chat_file.write('<tbody>\n'.encode('utf-8'))
        for y in i.msg_list:

            # Determine type of content
            content_type = None
            if mode == ANDROID:
                if y.from_me == 1:
                    if y.status == 6:
                        content_type = CONTENT_NEWGROUPNAME
                if content_type is None: 
                    if y.media_wa_type == "4":
                        content_type = CONTENT_VCARD
                        y.vcard_string = y.msg_text
                        y.vcard_name = y.local_url
                    elif y.media_wa_type == "1" or y.media_wa_type == "3" or y.media_wa_type == "5":
                        if str(y.msg_text)[:3] == "/9j":
                            y.media_thumb = "data:image/jpg;base64,\n" + y.msg_text
                        else:  
                            try:
                                y.media_thumb = "data:image/jpg;base64,\n" + base64.b64encode(y.media_thumb).decode("utf-8")
                            except:
                                y.media_thumb = ""
                        if y.media_wa_type == "5":
                            content_type = CONTENT_GPS
                            if y.local_url:
                                gpsname = y.local_url
                            else:
                                gpsname = None
                        else:
                            if y.media_wa_type == "3":
                                content_type = CONTENT_VIDEO
                            else:
                                content_type = CONTENT_IMAGE
                    elif y.media_wa_type == "2":
                        content_type = CONTENT_AUDIO
                    elif y.media_wa_type == "9":
                        content_type = CONTENT_MEDIA_DOC
                    elif y.media_wa_type == "10":
                        content_type = CONTENT_MISSED_CALL
                    elif y.media_wa_type == "11":
                        content_type = CONTENT_E2E
                    elif y.media_wa_type == "13":
                        content_type = CONTENT_GIF
                    elif y.media_wa_type == "14":
                        content_type = CONTENT_VCARDS
                    elif y.media_wa_type == "15":
                        content_type = CONTENT_DELETED_MSG
                    elif y.media_wa_type == "16":
                        content_type = CONTENT_LIVE_LOC
                    elif y.media_wa_type == "20":
                        content_type = CONTENT_STICKER            
                    else:
                        print ("y.media_wa_type = " + str(y.media_wa_type) + " ---> " + str(y.local_url))
                        content_type = CONTENT_TEXT
            # IPHONE mode
            elif mode == IPHONE:
                # prepare thumb
                if y.media_thumb: 
                    y.media_thumb = "data:image/jpg;base64,\n" + base64.b64encode(y.media_thumb).decode("utf-8")
                elif y.media_thumb_local_url:
                    y.media_thumb = y.media_thumb_local_url
                # Start if Clause
                # GPS
                if y.latitude and y.longitude:
                    content_type = CONTENT_GPS
                    y.media_wa_type = "5"
                    gpsname = None
                # VCARD
                elif y.vcard_string:
                    content_type = CONTENT_VCARD
                    y.media_wa_type = "4"
                # AUDIO?
                # MEDIA
                elif y.media_url:
                    if y.media_thumb:
                        if y.media_wa_type == "3":
                            content_type = CONTENT_VIDEO
                        else:
                            content_type = CONTENT_IMAGE
                            y.media_wa_type = "1"
                        #content_type = CONTENT_MEDIA_THUMB
                    else:
                        content_type = CONTENT_MEDIA_NOTHUMB     
                # TEXT
                elif y.msg_text is not None:
                    content_type = CONTENT_TEXT
                    y.media_wa_type = "0"
                # End if Clause

            # row class selection
            if content_type == CONTENT_NEWGROUPNAME:
               chat_file.write('<tr class="newgroupname">\n'.encode('utf-8'))
            elif y.from_me == 1:
                chat_file.write('<tr class="me">\n'.encode('utf-8'))
            else:
                chat_file.write('<tr class="other">\n'.encode('utf-8'))

            # get corresponding contact name for the contact_from of this message:
            if y.contact_from != "me":
                if y.contact_from == i.contact_id: #if sender is identical to chat name
                    y.contact_from = contactname
                else: # for group chats
                    for n in chat_session_list:
                        if n.contact_id == y.contact_from:
                            y.contact_from = convertsmileys ( n.contact_name )

            # PK  
            chat_file.write('<td>{}</td>\n'.format(y.pk_msg).encode('utf-8'))

            # Chat name (not used because of multiple files)
            #chat_file.write('<td class="contact">{}</td>\n'.format(contactname).encode('utf-8'))
            # Msg date
            chat_file.write('<td>{}</td>\n'.format(str(y.msg_date).replace(" ","&nbsp;")).encode('utf-8'))
            # From
            chat_file.write('<td class="contact">{}</td>\n'.format(y.contact_from).encode('utf-8'))
            
            # date elaboration for further use     
            date = str(y.msg_date)[:10]
            if date != 'N/A' and date != 'N/A error':
                date = int(date.replace("-",""))

            # Display Msg content (Text/Media)
            
            try:              
                if content_type == CONTENT_IMAGE:
                    #Search for offline file with current date (+3 days) and known media size                   
                    linkimage = findfile ("IMG", y.media_size, y.local_url, date, 3)
                    try:
                        chat_file.write('<td class="text"><a onclick="image(this.href);return(false);" target="image" href="{}"><img src="{}" alt="Image"/></a>'.format(linkimage, y.media_thumb).encode('utf-8'))
                    except:
                        chat_file.write('<td class="text">Image N/A'.encode('utf-8'))
                elif content_type == CONTENT_GIF:
                    #Search for offline file with current date (+3 days) and known media size                   
                    linkvideo = findfile ("GIF", y.media_size, y.local_url, date, 3)
                    try:
                        chat_file.write('<td class="text"><a onclick="media(this.href);return(false);" target="media" href="{}">GIF</a>'.format(linkvideo, mduration).encode('utf-8'))
                    except:
                        chat_file.write('<td class="text">GIF N/A'.encode('utf-8'))
                elif content_type == CONTENT_AUDIO:
                    #Search for offline file with current date (+3 days) and known media size
                    linkaudio = findfile ("PTT", y.media_size, y.local_url, date, 3)
                    if linkaudio[-1] == "/":
                        linkaudio = findfile ("AUD", y.media_size, y.local_url, date, 3)
                    if y.media_duration == "":
                        mduration = ""
                    else:
                        mduration = "({0} Sek.)".format(y.media_duration)
                    try:
                        chat_file.write('<td class="text"><a onclick="media(this.href);return(false);" target="media" href="{}">Audio</a> {}'.format(linkaudio, mduration).encode('utf-8'))
                    except:
                        chat_file.write('<td class="text">Audio N/A'.encode('utf-8'))
                elif content_type == CONTENT_VIDEO:
                    #Search for offline file with current date (+3 days) and known media size
                    linkvideo = findfile ("VID", y.media_size, y.local_url, date, 3)
                    if y.media_duration == "":
                        mduration = ""
                    else:
                        mduration = "({0} Sek.)".format(y.media_duration)
                    try:
                        chat_file.write('<td class="text"><a onclick="media(this.href);return(false);" target="media" href="{}"><img src="{}" alt="Video"/></a> {}'.format(linkvideo, y.media_thumb, mduration).encode('utf-8'))
                    except:
                        chat_file.write('<td class="text">Video N/A'.encode('utf-8'))
                elif content_type == CONTENT_MEDIA_THUMB:
                    #Search for offline file with current date (+3 days) and known media size                   
                    linkmedia = findfile ("MEDIA_THUMB", y.media_size, y.local_url, date, 3)
                    try:
                        chat_file.write('<td class="text"><a onclick="image(this.href);return(false);" target="image" href="{}"><img src="{}" alt="Media"/></a>'.format(linkmedia, y.media_thumb).encode('utf-8'))
                    except:
                        chat_file.write('<td class="text">Media N/A'.encode('utf-8'))
                elif content_type == CONTENT_MEDIA_NOTHUMB:
                    #Search for offline file with current date (+3 days) and known media size                    
                    linkmedia = findfile ("MEDIA_NOTHUMB", y.media_size, y.local_url, date, 3)
                    try:
                        chat_file.write('<td class="text"><a onclick="media(this.href);return(false);" target="media" href="{}">Media</a>'.format(linkmedia).encode('utf-8'))
                    except:
                        chat_file.write('<td class="text">Media N/A'.encode('utf-8'))  
                elif content_type == CONTENT_MEDIA_DOC:
                    #Search for offline file with current date (+3 days) and known media size                    
                    linkmedia = findfile ("DOC", y.media_size, y.local_url, date, 3)
                    try:
                        chat_file.write('<td class="text"><a onclick="media(this.href);return(false);" target="media" href="{}">DOCUMENT</a>'.format(linkmedia).encode('utf-8'))
                    except:
                        chat_file.write('<td class="text">Media N/A'.encode('utf-8'))
                elif content_type == CONTENT_MISSED_CALL:
                    try:
                        chat_file.write('<td class="text">Missed Voice Call'.encode('utf-8'))
                    except:
                        chat_file.write('<td class="text">Media N/A'.encode('utf-8'))
                elif content_type == CONTENT_E2E:
                    chat_file.write('<td class="text"><i>Message Encrypted</i>'.encode('utf-8'))  
                elif content_type == CONTENT_VCARD:
                    if y.vcard_name == "" or y.vcard_name is None:
                        vcardintro = ""
                    else:
                        vcardintro = "CONTACT: <b>" + y.vcard_name + "</b><br>\n"
                    y.vcard_string = y.vcard_string.replace ("\n", "<br>\n")
                    try:
                        chat_file.write('<td class="text">{}'.format(vcardintro + y.vcard_string).encode('utf-8'))
                    except:
                        chat_file.write('<td class="text">VCARD N/A'.encode('utf-8'))
                elif content_type == CONTENT_GPS:
                    try:
                        if gpsname == "" or gpsname == None:
                            gpsname = ""
                        else:
                            gpsname = "\n" + gpsname
                        gpsname = gpsname.replace ("\n", "<br>\n")
                        if y.media_thumb:
                            chat_file.write('<td class="text"><a onclick="image(this.href);return(false);" target="image" href="https://maps.google.com/?q={},{}"><img src="{}" alt="GPS"/></a>{}'.format(y.latitude, y.longitude, y.media_thumb, gpsname).encode('utf-8'))
                        else:
                            chat_file.write('<td class="text"><a onclick="image(this.href);return(false);" target="image" href="https://maps.google.com/?q={},{}">GPS: {}, {}</a>{}'.format(y.latitude, y.longitude, y.latitude, y.longitude, gpsname).encode('utf-8'))
                    except:
                        chat_file.write('<td class="text">GPS N/A'.encode('utf-8'))
                elif content_type == CONTENT_LIVE_LOC:
                    try:
                        if gpsname == "" or gpsname == None:
                            gpsname = ""
                        else:
                            gpsname = "\n" + gpsname
                        gpsname = gpsname.replace ("\n", "<br>\n")
                        live_loc_end = datetime.datetime.fromtimestamp(int(y.local_url[-13:])/1000).strftime('%c')
                        chat_file.write('<td class="text"><a onclick="image(this.href);return(false);" target="image" href="https://maps.google.com/?q={},{}">GPS: {}, {} </a>{}<br>UPTO: {}'.format(y.latitude, y.longitude, y.latitude, y.longitude, gpsname, live_loc_end).encode('utf-8'))
                    except:
                        chat_file.write('<td class="text">GPS N/A'.encode('utf-8'))
                elif content_type == CONTENT_DELETED_MSG:
                    try:
                        chat_file.write('<td class="text"><i>Message Deleted</i>'.encode('utf-8'))
                    except:
                        chat_file.write('<td class="text">N/A'.encode('utf-8'))
                elif content_type == CONTENT_STICKER:
                    if y.local_url is not None:
                        sticker_name = "STICKER: " + str(y.local_url)
                    else:
                        sticker_name = "STICKER"
                    try:
                        chat_file.write('<td class="text"><i>{}</i>'.format(sticker_name).encode('utf-8'))
                    except:
                        chat_file.write('<td class="text">N/A'.encode('utf-8'))
                elif content_type == CONTENT_VCARDS:
                    if y.media_thumb is not None and y.key_id is not None:
                        vcard_fname = str(y.key_id)+".vcards.txt"
                        try:
                            f = open(vcard_fname, "w+")
                            f.write(str(y.media_thumb))
                            f.close()
                            chat_file.write('<td class="text"><a onclick="media(this.href);return(false);" target="media" href="{}">{}</a>'.format(vcard_fname, str(y.local_url)).encode('utf-8'))
                        except:
                            chat_file.write('<td class="text">{}'.format(str(y.local_url).encode('utf-8')))
                    else:
                        chat_file.write('<td class="text">VCARDS N/A'.encode('utf-8'))
                elif content_type == CONTENT_NEWGROUPNAME:
                    content_type = CONTENT_OTHER
                elif content_type != CONTENT_TEXT:
                    content_type = CONTENT_OTHER
                # End of If-Clause, now text or other type of content:
                if content_type == CONTENT_TEXT or content_type == CONTENT_OTHER:         
                    msgtext = convertsmileys ( y.msg_text )
                    msgtext = re.sub(r'(http[^\s\n\r]+)', r'<a onclick="image(this.href);return(false);" target="image" href="\1">\1</a>', msgtext)
                    msgtext = re.sub(r'((?<!\S)www\.[^\s\n\r]+)', r'<a onclick="image(this.href);return(false);" target="image" href="http://\1">\1</a>', msgtext)
                    msgtext = msgtext.replace ("\n", "<br>\n")
                    try:
                        chat_file.write('<td class="text">{}'.format(msgtext).encode('utf-8'))
                    except:
                        chat_file.write('<td class="text">N/A'.encode('utf-8'))
            except:
                #print ("error in message id " + y.pk_msg + "(key_id: " + y.key_id + ")")
                print ("error in message id X")
                chat_file.write('<td class="text">N/A (error in message)'.encode('utf-8'))
            # chat_file.write(str(content_type)) #Debug
            chat_file.write('</td>\n'.encode('utf-8'))
            
            # Msg status
            chat_file.write('<td>{}</td>\n'.format(y.status).encode('utf-8'))

            # Media type
            chat_file.write('<td>{}</td>\n'.format(y.media_wa_type).encode('utf-8'))

            # Media size
            chat_file.write('<td>{}</td>\n'.format(y.media_size).encode('utf-8'))
            chat_file.write('</tr>\n'.encode('utf-8'))
            
        chat_file.write('</tbody>\n'.encode('utf-8'))       
        # writes 1st table footer
        chat_file.write('</table>\n'.encode('utf-8'))
        
        # Close chat file
        outputfile_close(chat_file);

    # writes page footer        
    #wfile.write('</body></html>\n'.encode('utf-8'))
    #wfile.close()
    print ("done!")

    #END 
    #webbrowser.open(outfile)            
 

##### GLOBAL variables #####

PYTHON_VERSION = None
testtext = ""
testtext = testtext.replace('\ue40e', 'v3')
if testtext == "v3":    
    PYTHON_VERSION = 3
    print ("Python Version 3.x")
else:
    PYTHON_VERSION = 2
    print ("Python Version 2.x")
    reload(sys)
    sys.setdefaultencoding( "utf-8" )
    import convert_smileys_python_2


mode    = None
IPHONE  = 1
ANDROID = 2

content_type          = None
CONTENT_TEXT          = 0
CONTENT_IMAGE         = 1
CONTENT_AUDIO         = 2
CONTENT_VIDEO         = 3
CONTENT_VCARD         = 4
CONTENT_GPS           = 5
CONTENT_NEWGROUPNAME  = 6
CONTENT_MEDIA_THUMB   = 7
CONTENT_MEDIA_NOTHUMB = 8
CONTENT_MEDIA_DOC     = 9
CONTENT_MISSED_CALL   = 10
CONTENT_E2E           = 11
CONTENT_GIF           = 13
CONTENT_VCARDS        = 14
CONTENT_DELETED_MSG   = 15
CONTENT_LIVE_LOC      = 16
CONTENT_STICKER       = 20
CONTENT_OTHER         = 99

flistvid = {}
flistaud = {}
flistimg = {}
flistptt = {}
flistdoc = {}
flistgif = {}

css_style = """
<style type="text/css">
body {
    font-family: calibri;
    background-color: #f5f5f5;
}
h1 {
    font-family: courier;
    font-style:italic;
    color: #444444;
}
h2 {
    font-style:italic;
    color: #444444;
}
h3 {
    font-style:italic;
}
table {
    text-align: center;
}
th {
    font-style:italic;
}
td.text {
    width: 600px;
    text-align: left;
}
td.contact {
    width: 250px;
}
tr.even {
    background-color: #DDDDDD
}
tr.me {
    background-color: #88FF88;
}
tr.other {
    background-color: #F5F5F5;
}
tr.newgroupname {
    background-color: #FFCC33;
}
</style>
"""

popups = """
function media( url )
{
  if (typeof(newwindow) !== "undefined" && !newwindow.closed)
  {
    newwindow.close();
  } else
  {
  }
  newwindow=window.open("about:blank", "media", "menubar=0,location=1");
  newwindow.document.write('<html><body><embed src="' + url + '" width="800" height="600" /></body></html>');
  //newwindow.document.write('<video src="' + url + '" controls="controls">video doesn't work</video>');
}

function image( url )
{
  if (typeof(imagewindow) !== "undefined" && !imagewindow.closed)
  {
    imagewindow=window.open(url,'image','menubar=0,location=1');
    imagewindow.focus();
  } else
  {
    imagewindow=window.open(url,'image','menubar=0,location=1');
  }
}
"""

sortable = """
/*
Table sorting script  by Joost de Valk, check it out at http://www.joostdevalk.nl/code/sortable-table/.
Based on a script from http://www.kryogenix.org/code/browser/sorttable/.
Distributed under the MIT license: http://www.kryogenix.org/code/browser/licence.html .

Copyright (c) 1997-2007 Stuart Langridge, Joost de Valk.

Version 1.5.7
*/

/* You can change these values */
var image_path = "data/sort-table/";
var image_up = "arrow-up.gif";
var image_down = "arrow-down.gif";
var image_none = "arrow-none.gif";
var europeandate = true;
var alternate_row_colors = true;

/* Don't change anything below this unless you know what you're doing */
addEvent(window, "load", sortables_init);

var SORT_COLUMN_INDEX;
var thead = false;

function sortables_init() {
    // Find all tables with class sortable and make them sortable
    if (!document.getElementsByTagName) return;
    tbls = document.getElementsByTagName("table");
    for (ti=0;ti<tbls.length;ti++) {
        thisTbl = tbls[ti];
        if (((' '+thisTbl.className+' ').indexOf("sortable") != -1) && (thisTbl.id)) {
            ts_makeSortable(thisTbl);
        }
    }
}

function ts_makeSortable(t) {
    if (t.rows && t.rows.length > 0) {
        if (t.tHead && t.tHead.rows.length > 0) {
            var firstRow = t.tHead.rows[t.tHead.rows.length-1];
            thead = true;
        } else {
            var firstRow = t.rows[0];
        }
    }
    if (!firstRow) return;
    
    // We have a first row: assume it's the header, and make its contents clickable links
    for (var i=0;i<firstRow.cells.length;i++) {
        var cell = firstRow.cells[i];
        var txt = ts_getInnerText(cell);
        if (cell.className != "unsortable" && cell.className.indexOf("unsortable") == -1) {
            cell.innerHTML = '<a href="#" class="sortheader" onclick="ts_resortTable(this, '+i+');return false;">'+txt+'<span class="sortarrow">&nbsp;&nbsp;&darr;</span></a>';
        }
    }
    if (alternate_row_colors) {
        alternate(t);
    }
}

function ts_getInnerText(el) {
    if (typeof el == "string") return el;
    if (typeof el == "undefined") { return el };
    if (el.innerText) return el.innerText;    //Not needed but it is faster
    var str = "";
    
    var cs = el.childNodes;
    var l = cs.length;
    for (var i = 0; i < l; i++) {
        switch (cs[i].nodeType) {
            case 1: //ELEMENT_NODE
                str += ts_getInnerText(cs[i]);
                break;
            case 3:    //TEXT_NODE
                str += cs[i].nodeValue;
                break;
        }
    }
    return str;
}

function ts_resortTable(lnk, clid) {
    var span;
    for (var ci=0;ci<lnk.childNodes.length;ci++) {
        if (lnk.childNodes[ci].tagName && lnk.childNodes[ci].tagName.toLowerCase() == 'span') span = lnk.childNodes[ci];
    }
    var spantext = ts_getInnerText(span);
    var td = lnk.parentNode;
    var column = clid || td.cellIndex;
    var t = getParent(td,'TABLE');
    // Work out a type for the column
    if (t.rows.length <= 1) return;
    var itm = "";
    var i = 0;
    while (itm == "" && i < t.tBodies[0].rows.length) {
        var itm = ts_getInnerText(t.tBodies[0].rows[i].cells[column]);
        itm = trim(itm);
        if (itm.substr(0,4) == "<!--" || itm.length == 0) {
            itm = "";
        }
        i++;
    }
    if (itm == "") return; 
    sortfn = ts_sort_caseinsensitive;
    if (itm.match(/^\d\d[\/\.-][a-zA-z][a-zA-Z][a-zA-Z][\/\.-]\d\d\d\d$/)) sortfn = ts_sort_date;
    if (itm.match(/^\d\d[\/\.-]\d\d[\/\.-]\d\d\d{2}?$/)) sortfn = ts_sort_date;
    if (itm.match(/^-?[£$€Û¢´]\d/)) sortfn = ts_sort_numeric;
    if (itm.match(/^-?(\d+[,\.]?)+(E[-+][\d]+)?%?$/)) sortfn = ts_sort_numeric;
    SORT_COLUMN_INDEX = column;
    var firstRow = new Array();
    var newRows = new Array();
    for (k=0;k<t.tBodies.length;k++) {
        for (i=0;i<t.tBodies[k].rows[0].length;i++) { 
            firstRow[i] = t.tBodies[k].rows[0][i]; 
        }
    }
    for (k=0;k<t.tBodies.length;k++) {
        if (!thead) {
            // Skip the first row
            for (j=1;j<t.tBodies[k].rows.length;j++) { 
                newRows[j-1] = t.tBodies[k].rows[j];
            }
        } else {
            // Do NOT skip the first row
            for (j=0;j<t.tBodies[k].rows.length;j++) { 
                newRows[j] = t.tBodies[k].rows[j];
            }
        }
    }
    newRows.sort(sortfn);
    if (span.getAttribute("sortdir") == 'down') {
            ARROW = '&nbsp;&nbsp;&darr;';
            newRows.reverse();
            span.setAttribute('sortdir','up');
    } else {
            ARROW = '&nbsp;&nbsp;&uarr;';
            span.setAttribute('sortdir','down');
    } 
    // We appendChild rows that already exist to the tbody, so it moves them rather than creating new ones
    // don't do sortbottom rows
    for (i=0; i<newRows.length; i++) { 
        if (!newRows[i].className || (newRows[i].className && (newRows[i].className.indexOf('sortbottom') == -1))) {
            t.tBodies[0].appendChild(newRows[i]);
        }
    }
    // do sortbottom rows only
    for (i=0; i<newRows.length; i++) {
        if (newRows[i].className && (newRows[i].className.indexOf('sortbottom') != -1)) 
            t.tBodies[0].appendChild(newRows[i]);
    }
    // Delete any other arrows there may be showing
    var allspans = document.getElementsByTagName("span");
    for (var ci=0;ci<allspans.length;ci++) {
        if (allspans[ci].className == 'sortarrow') {
            if (getParent(allspans[ci],"table") == getParent(lnk,"table")) { // in the same table as us?
                allspans[ci].innerHTML = '&nbsp;&nbsp;&darr;';
            }
        }
    }        
    span.innerHTML = ARROW;
    alternate(t);
}

function getParent(el, pTagName) {
    if (el == null) {
        return null;
    } else if (el.nodeType == 1 && el.tagName.toLowerCase() == pTagName.toLowerCase()) {
        return el;
    } else {
        return getParent(el.parentNode, pTagName);
    }
}

function sort_date(date) {    
    // y2k notes: two digit years less than 50 are treated as 20XX, greater than 50 are treated as 19XX
    dt = "00000000";
    if (date.length == 11) {
        mtstr = date.substr(3,3);
        mtstr = mtstr.toLowerCase();
        switch(mtstr) {
            case "jan": var mt = "01"; break;
            case "feb": var mt = "02"; break;
            case "mar": var mt = "03"; break;
            case "apr": var mt = "04"; break;
            case "may": var mt = "05"; break;
            case "jun": var mt = "06"; break;
            case "jul": var mt = "07"; break;
            case "aug": var mt = "08"; break;
            case "sep": var mt = "09"; break;
            case "oct": var mt = "10"; break;
            case "nov": var mt = "11"; break;
            case "dec": var mt = "12"; break;
            // default: var mt = "00";
        }
        dt = date.substr(7,4)+mt+date.substr(0,2);
        return dt;
    } else if (date.length == 10) {
        if (europeandate == false) {
            dt = date.substr(6,4)+date.substr(0,2)+date.substr(3,2);
            return dt;
        } else {
            dt = date.substr(6,4)+date.substr(3,2)+date.substr(0,2);
            return dt;
        }
    } else if (date.length == 8) {
        yr = date.substr(6,2);
        if (parseInt(yr) < 50) { 
            yr = '20'+yr; 
        } else { 
            yr = '19'+yr; 
        }
        if (europeandate == true) {
            dt = yr+date.substr(3,2)+date.substr(0,2);
            return dt;
        } else {
            dt = yr+date.substr(0,2)+date.substr(3,2);
            return dt;
        }
    }
    return dt;
}

function ts_sort_date(a,b) {
    dt1 = sort_date(ts_getInnerText(a.cells[SORT_COLUMN_INDEX]));
    dt2 = sort_date(ts_getInnerText(b.cells[SORT_COLUMN_INDEX]));
    
    if (dt1==dt2) {
        return 0;
    }
    if (dt1<dt2) { 
        return -1;
    }
    return 1;
}
function ts_sort_numeric(a,b) {
    var aa = ts_getInnerText(a.cells[SORT_COLUMN_INDEX]);
    aa = clean_num(aa);
    var bb = ts_getInnerText(b.cells[SORT_COLUMN_INDEX]);
    bb = clean_num(bb);
    return compare_numeric(aa,bb);
}
function compare_numeric(a,b) {
    var a = parseFloat(a);
    a = (isNaN(a) ? 0 : a);
    var b = parseFloat(b);
    b = (isNaN(b) ? 0 : b);
    return a - b;
}
function ts_sort_caseinsensitive(a,b) {
    aa = ts_getInnerText(a.cells[SORT_COLUMN_INDEX]).toLowerCase();
    bb = ts_getInnerText(b.cells[SORT_COLUMN_INDEX]).toLowerCase();
    if (aa==bb) {
        return 0;
    }
    if (aa<bb) {
        return -1;
    }
    return 1;
}
function ts_sort_default(a,b) {
    aa = ts_getInnerText(a.cells[SORT_COLUMN_INDEX]);
    bb = ts_getInnerText(b.cells[SORT_COLUMN_INDEX]);
    if (aa==bb) {
        return 0;
    }
    if (aa<bb) {
        return -1;
    }
    return 1;
}
function addEvent(elm, evType, fn, useCapture)
// addEvent and removeEvent
// cross-browser event handling for IE5+,    NS6 and Mozilla
// By Scott Andrew
{
    if (elm.addEventListener){
        elm.addEventListener(evType, fn, useCapture);
        return true;
    } else if (elm.attachEvent){
        var r = elm.attachEvent("on"+evType, fn);
        return r;
    } else {
        alert("Handler could not be removed");
    }
}
function clean_num(str) {
    str = str.replace(new RegExp(/[^-?0-9.]/g),"");
    return str;
}
function trim(s) {
    return s.replace(/^\s+|\s+$/g, "");
}
function alternate(table) {
    // Take object table and get all it's tbodies.
    var tableBodies = table.getElementsByTagName("tbody");
    // Loop through these tbodies
    for (var i = 0; i < tableBodies.length; i++) {
        // Take the tbody, and get all it's rows
        var tableRows = tableBodies[i].getElementsByTagName("tr");
        // Loop through these rows
        // Start at 1 because we want to leave the heading row untouched
        for (var j = 0; j < tableRows.length; j++) {
            // Check if j is even, and apply classes for both possible results
            if ( (j % 2) == 0  ) {
                if ( !(tableRows[j].className.indexOf('odd') == -1) ) {
                    tableRows[j].className = tableRows[j].className.replace('odd', 'even');
                } else {
                    if ( tableRows[j].className.indexOf('even') == -1 ) {
                        tableRows[j].className += " even";
                    }
                }
            } else {
                if ( !(tableRows[j].className.indexOf('even') == -1) ) {
                    tableRows[j].className = tableRows[j].className.replace('even', 'odd');
                } else {
                    if ( tableRows[j].className.indexOf('odd') == -1 ) {
                        tableRows[j].className += " odd";
                    }
                }
            } 
        }
    }
}
"""

if __name__ == '__main__':
    main(sys.argv[1:])

