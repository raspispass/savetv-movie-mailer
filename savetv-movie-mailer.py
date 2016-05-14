#!/usr/bin/env python
# -*- coding: iso-8859-1 -*-

# General Imorts
import requests
from time import *
import time
import datetime
from datetime import datetime, date
from datetime import datetime, timedelta
import sqlite3
import sys
import os.path
import shutil
import httplib
from savetv import SaveTV
import json
import re
import getopt

# Imports for mail transfer (considering UTF8 and German Umlaute)
import smtplib
from cStringIO import StringIO
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.header import Header
from email import Charset
from email.generator import Generator

# Unicode Workaround (Umlaute etc.)
import sys
reload(sys)
sys.setdefaultencoding("utf-8")


#########################
# Configuration
#########################

# SaveTV configuration (implemented in savetv.py)
savetv_username = ""
savetv_password = ""
movielist_filename = ""

# Mail configuration
from_address = ['RaspiVDR', 'savetv@domain.com']
recipient = ['Raspispass', 'raspispass@domain.com']
subject = "[RaspVDR] Neue Film-Treffer in Save.TV"
smtpserver = 'smtp.domain.com'
smtp_username = "savetv@domain.com"
smtp_password = "smtp-password"


########################
# Helpers
########################
# Used for Regex in SQLite db
def regexp(expr, item):
    reg = re.compile(expr, re.IGNORECASE)
    return reg.search(item) is not None

########################
# SaveTV connection
########################
def connect_savetv_server(username, password):
    print "[-] Connect to SaveTV server:"
    client = SaveTV(language='de-DE',items_per_page=5000) # 5000 is max

    #Request auth token
    client.request_access_token()

    print "    [*] Access Token:\t" + str(client.access_token)
    print "    [*] Session Expire:\t" + str(client.expires_in)
    print "    [*] Refresh Token:\t" + str(client.refresh_token)

    print "[*] Authentication succeeded"
    return client

########################
# SaveTV: Fetch all movies (category=1) and store in recordings database
########################
def savetv_fetch_movies(client_savetv, con_savetv_db):

    print "[-] Fetch SaveTV recordings:\n"
    recordings = client_savetv.get_recordings(category=1, subcategory=None, channel=None, ishighlight=None, q=None, station=None, minstartdate=None, maxstartdate= None, sort= None, max_results= -2)

    print "------------------------------------------------------------------------"
    print "[-] TotalCound:\t" + str(recordings['paging']['totalCount'])
    print "[-] Limit:\t" + str(recordings['paging']['limit'])
    print "[-] Offset:\t" + str(recordings['paging']['offset'])
    print "------------------------------------------------------------------------"

    # Store in recordings database
    for rec in recordings['items']:
        telecast_id = rec['telecast']['id']
        title = rec['telecast']['title'].encode("utf-8")
        subtitle = rec['telecast']['subTitle'].encode("utf-8")
        descr = rec['telecast']['description'].encode("utf-8")
        dlformat = "" # TODO
        logo = rec['telecast']['imageUrl100'].encode("utf-8") # Alternativ: imageUrl250 oder imageUrl500
        imdb_rating = get_imdb_rating(title)
        print "    [*] " + title.encode("utf-8") + " (IMDB: " + imdb_rating + ")"
        # Workaround wegen Unicode
        con_savetv_db.text_factory = str
        with con_savetv_db:
            cur = con_savetv_db.cursor()
            cur.execute("INSERT INTO recordings (telecast_id,title,subtitle,description,format,logo,imdbrating) values (?, ?, ?, ?, ?, ?, ?)",(telecast_id,title,subtitle,descr,dlformat,logo,imdb_rating))
        con_savetv_db.commit()

########################
#Get IMDB Rating (from www.omdbapi.com)
########################
#http://www.omdbapi.com/?t=Der+General&y=&plot=short&r=json
def get_imdb_rating(movie_title):
    # headers
    headers = {'Host': 'www.omdbapi.com',
               'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/39.0.2171.36 Safari/537.36',
               'Accept-Encoding': 'gzip, deflate'}
    url = 'http://www.omdbapi.com/'
    params = {'t': movie_title,'plot':'short','r':'json'}
    result = requests.get(url, params=params, headers=headers, verify=False)
    json_data = result.json()
    try:
        rating = json_data['imdbRating']
        return rating
    except Exception:    
        return ""

########################
# Init SQLite DB ("matched results" DB)
########################
def init_and_connect_matched_results_DB(db_filename):
    print("[*] Using pysqlite version " + str(sqlite3.version))
    print("[*] Using SQLite version " + str(sqlite3.sqlite_version))

    # Init Matched Results Database
    try:
        connection = sqlite3.connect(db_filename)
        print("[*] Connected to SQLite database " + db_filename)
        with connection:
            cur = connection.cursor()
            cur.execute("DROP TABLE IF EXISTS matched_movies")
            cur.execute("CREATE TABLE matched_movies(telecast_id INT, title TEXT, subtitle TEXT, description TEXT, format TEXT, logo TEXT, imdbrating TEXT, report_reason TEXT, regexp_match TEXT)")
        connection.commit()
        print("[*] Created new SQLite database " + db_filename)
        return connection
    except sqlite3.Error:
        if connection:
            connection.rollback()
        print("[*] Error %s:" % sqlite3.Error.args[0])
        sys.exit(1)


########################
# Init SQLite DB ("savetv recordings" DB)
########################
def init_and_connect_savetv_recordings_DB(db_savetv):
    print("[*] Using pysqlite version " + str(sqlite3.version))
    print("[*] Using SQLite version " + str(sqlite3.sqlite_version))

    # Init SaveTV Recordings Database
    try:
        connection = sqlite3.connect(':memory:')
        connection = sqlite3.connect(db_savetv)
        connection.create_function("REGEXP", 2, regexp)
        print("[*] Connected to SQLite database " + db_savetv)
        with connection:
            cur = connection.cursor()
            cur.execute("DROP TABLE IF EXISTS recordings")
            cur.execute("CREATE TABLE recordings(telecast_id INT, title TEXT, subtitle TEXT, description TEXT, format TEXT, logo TEXT, imdbrating TEXT, report_reason TEXT, regexp_match TEXT)")
        connection.commit()
        print("[*] Created new SQLite database " + db_savetv)
        return connection
    except sqlite3.Error:
        if connection:
            connection.rollback()
        print("[*] Error %s:" % sqlite3.Error.args[0])
        sys.exit(1)


########################
# Disconnect SQLite DB 
########################
def disconnectDB(connection):
    if connection:
        connection.close()
    print("[*] Disconnected from DB ")


########################
# Search in SaveTV database for REGEXP matches
########################
def match_fileEntries_with_saveTV_recordings(movielist_filename, con_savetv_db, con_matched_results_db):
    # Iterate through the Most Wanted Movie List and search in savetv_recordings
    with open(movielist_filename) as f:
        for line in f:
           # Strip the newline
           line = line.rstrip('\n')
           # Query in saveTV recordings database with regexp ("LIKE")
           print "[*] Searching for regular expression in recordings database: " + line

           cur = con_savetv_db.cursor()
           #telecast_id INT, title TEXT, subtitle TEXT, description TEXT, format TEXT, logo TEXT)
           cur.execute("SELECT telecast_id,title,subtitle,description,format,logo,imdbrating FROM recordings WHERE title REGEXP ? OR description REGEXP ?", [line,line])
           matched_recordings = cur.fetchall()
         
           if len(matched_recordings) > 0:
               print "[*] Match(es) found! (" + str(len(matched_recordings)) + ")"
               for rec in matched_recordings:
                   telecast_id = rec[0]
                   title = rec[1]
                   subtitle = rec[2]
                   description = rec[3]
                   dlformat = rec[4]
                   logo = rec[5]
                   imdb_rating = rec[6]
                   report_reason = "RegExp"

               # Workaround wegen Unicode
               con_matched_results_db.text_factory = str

               # Write matched results into matched results database
               with con_matched_results_db:
                   # First check for already inserted movies (multiple regex matches on the same movie)
                   cur = con_matched_results_db.cursor()
                   cur.execute("SELECT DISTINCT title FROM matched_movies WHERE title = ?", [title])
                   duplicate_entry_counter = len(cur.fetchall())
                   if duplicate_entry_counter == 0:
                       cur.execute("INSERT INTO matched_movies(telecast_id,title,subtitle,description,format,logo,imdbrating,report_reason,regexp_match) values (?, ?, ?, ?, ?, ?, ?, ?, ?)",(telecast_id,title,subtitle,description,dlformat,logo,imdb_rating,report_reason,line))
                       con_matched_results_db.commit()
                   else:
                       print "[*] Movie already in database - ignored"

           # No regexp match
           else:
                #print "[*] No match"
                pass



########################
# Add great IMDB rated movies
########################
def add_great_imdb_rated_movies(con_savetv_db, con_matched_results_db,rating=8):
    # Filter movies higher than imdb rating
    cur = con_savetv_db.cursor()
    cur.execute("SELECT DISTINCT telecast_id,title,subtitle,description,format,logo,imdbrating FROM recordings WHERE imdbrating >= ? and imdbrating <> 'N/A' GROUP BY telecast_id", [rating])
    matched_recordings = cur.fetchall()

    if len(matched_recordings) > 0:
        print "[*] IMDB Match(es) found! (" + str(len(matched_recordings)) + ")"
        for rec in matched_recordings:
            telecast_id = rec[0]
            title = rec[1]
            subtitle = rec[2]
            description = rec[3]
            dlformat = rec[4]
            logo = rec[5]
            imdb_rating = rec[6]
            report_reason = "IMDB"

            # Workaround wegen Unicode
            con_matched_results_db.text_factory = str

            # Write matched results into matched results database
            with con_matched_results_db:
                # First check for already inserted movies
                cur = con_matched_results_db.cursor()
                cur.execute("SELECT DISTINCT title FROM matched_movies WHERE title = ?", [title])
                duplicate_entry_counter = len(cur.fetchall())
                if duplicate_entry_counter == 0:
                    cur.execute("INSERT INTO matched_movies(telecast_id,title,subtitle,description,format,logo,imdbrating,report_reason) values (?, ?, ?, ?, ?, ?, ?, ?)",(telecast_id,title,subtitle,description,dlformat,logo,imdb_rating,report_reason))
                    con_matched_results_db.commit()
                    print "[*] Added movie for IMDB rating: " + title
                else:
                    print "[*] Movie already in database - ignored"

    else:
        print "[*] There are no IMDB movies rated higher than " + str(rating)

########################
# Generate HTML output for Mail
########################
def query_and_generate_HTML_from_DB(connection):
    # HTML result for the email
    html_result = ""

    cur = connection.cursor()
    # Title and description as a unique identifier for one movie
    cur.execute("SELECT DISTINCT telecast_id,title,subtitle,description,format,logo,imdbrating,report_reason,regexp_match FROM matched_movies GROUP BY title")
    rows = cur.fetchall()

    for row in rows:
        telecast_id = row[0]
        title = row[1]
        subtitle = row[2]
        descr = row[3]
        logo = row[5]
        imdb_rating = row[6]
        report_reason = row[7]
        regexp_match = row[8]

        print("[---------------")
        print("[-] Title:       " + title)
        print("[-] Description: " + descr)

        # HTML: Beginning of the movie section
	html_result += " <div class='movie'>\n"
        html_result += "  <div class='movie_header'>\n"
        html_result += "    <div class='titel'><a href='https://www.save.tv/STV/M/obj/archive/VideoArchiveDetails.cfm?TelecastId=" + str(telecast_id) + "'>" + title + "\n " + subtitle + "</a></div>\n"
        # Check for report_reason (IMDB or RegExp)
        if report_reason == "IMDB":
            html_result += "    <div class='imdb' style='color:red;'>IMDB: " + imdb_rating + "</div>\n"
	html_result += "  </div>\n"
	html_result += " <div class='movie_body'>\n"
	html_result += "    <div class='image'><img width=134px height=83px src='" + logo + "'/></div>\n"
        # Mark regexp match
        if report_reason == "RegExp":
            descr = re.sub(r"" + regexp_match  + "", "<span style='color:red;'>" + regexp_match + "</span>", descr)
	html_result += "    <div class='description'>" + descr + "</div>\n"
	html_result += " </div>\n"

        # HTML: Ending of the movie section
        html_result += "  </div>\n"
	html_result += "  \n<div style='height:50px'></div>\n\n"

    return html_result


########################
# Check for already transferred movies (prevent sending it twice)
########################
def checkUpdates(con_db, db_backup_filename, db_filename):

    # 1) Delete already mailed movies from the current search DB
    #    Check if backup DB already exists (history of already mailed movies)
    if os.path.isfile(db_backup_filename):
        try:
            con_db_backup = sqlite3.connect(db_backup_filename)
            print("[*] Connected to SQLite database " + db_backup_filename)

        except sqlite3.Error:
            if con_db_backup:
                con_db_backup.rollback()
            print("[*] Error %s:" % sqlite3.Error.args[0])
            sys.exit(1)

        # Workaround wegen Unicode
        con_db_backup.text_factory = str
        con_db.text_factory = str    
    
        cur_db = con_db.cursor()
        cur_db_backup = con_db_backup.cursor()

        # Title_id as a unique identifier for one movie
        cur_db.execute("SELECT DISTINCT title FROM matched_movies GROUP BY title")
        rows_db_title_id = cur_db.fetchall()
        cur_db_backup.execute("SELECT DISTINCT title FROM matched_movies GROUP BY title")
        rows_db_backup_title_id = cur_db_backup.fetchall()

        for row_db_title_id in rows_db_title_id:
            title_id_db = row_db_title_id[0]

            # Check for each movie (identified as: title_id) if it exists in the backup DB (history)
            for row_db_backup_title_id in rows_db_backup_title_id:
                # If title_id are the same (=> duplicate)
                if (title_id_db in row_db_backup_title_id):
                    title_id_db_backup = row_db_backup_title_id[0]
                    # Delete already known (and sent) movies from current search (db) 
                    cur_db.execute("DELETE FROM matched_movies WHERE title=?", (title_id_db,))
                    print ("[*] Record identified as duplicate and removed from result set: " + str(title_id_db))
     
        # 2) Add new search entries to the backup DB (history)
        cur_db.execute("SELECT DISTINCT title FROM matched_movies GROUP BY title")
        rows_db_title_id = cur_db.fetchall()
        cur_db_backup.execute("SELECT DISTINCT title FROM matched_movies GROUP BY title")
        rows_db_backup_title_id = cur_db_backup.fetchall()

        for row_db_title_id in rows_db_title_id:
            title_id_db = row_db_title_id[0]

            # Check for each movie (identified as: title_id) if it exists in the backup DB (history)
            for row_db_backup_title_id in rows_db_backup_title_id:
                # If title_id is NOT the same (=> new movie) it is added to the backup DB (history)
                if (title_id_db not in row_db_backup_title_id):
                    title_id_db_backup = row_db_backup_title_id[0]
                    cur_db_backup.execute("INSERT INTO matched_movies (telecast_id,title,subtitle,description,format,logo,imdbrating) values (?, ?, ?, ?, ?, ?, ?)",("",title_id_db,"","","","",""))
                    con_db_backup.commit()
                    print ("[*] Record added to the backup db (history): " + str(title_id_db))

    else:
        print("[*] No backup file yet exists ... creating one")
        shutil.copyfile(db_filename, db_backup_filename)

    # Check (for entries) if new movies were added
    cur_db = con_db.cursor()
    cur_db.execute("SELECT DISTINCT title FROM matched_movies GROUP BY title")
    # No new movies found
    if (len(cur_db.fetchall()) < 1):
        return False
    # New movies found
    else:
        return True


########################
# Send Email
########################
def sendMail(htmlmsg, from_address, recipient, subject):

    html = ""
    html += """
        <html>
        <head>
        <style>

        .movie_header {
            background-color: green;
            overflow:hidden;
            zoom:1;
            color: white;
            font-weight:bold;
        }
        .movie_body {
        }
        .imdb {
            text-align: right;
            padding-right: 1.5rem;
            padding-top: 1rem;
            padding-bottom: 1rem;
            float: right;
        }
        .report_reason {
           text-align: right;
            padding-right: 1.5rem;
            padding-top: 1rem;
            padding-bottom: 1rem;
            float: right;
        }
        .titel {
            text-align: left;
            padding-left: 1.5rem;
            float: left;
            padding-top: 1rem;
            padding-bottom: 1rem;
        }
        .description {
            padding-left: 1.5rem;
            padding-right: 1.5rem;
            padding-top: 1rem;
            padding-bottom: 1rem;
	    min-height: 51px;
        }
        .image {
            padding:0px;
            width: 134px;
            float: right;
            margin-left: 1rem;
            margin-bottom: 1rem;
        }

        /* unvisited link */
        a:link {
            color: white;
            text-decoration: none;
        }

        /* visited link */
        a:visited {
            color: white;
            text-decoration: none;
        }

        /* mouse over link */
        a:hover {
            color: lightgray;
            text-decoration: none;
        }

        /* selected link */
        a:active {
            color: white;
            text-decoration: none;
        }
        .movie {
            border: 1px solid green;
        }

        </style>
	</head>
        <body>
        """

    html += htmlmsg
    htmlpart = MIMEText(html, 'html', 'UTF-8')

    msg = MIMEMultipart('alternative')
    msg['Subject'] = "%s" % Header(subject, 'utf-8')
    # Only descriptive part of recipient and sender shall be encoded, not the email address
    msg['From'] = "\"%s\" <%s>" % (Header(from_address[0], 'utf-8'), from_address[1])
    msg['To'] = "\"%s\" <%s>" % (Header(recipient[0], 'utf-8'), recipient[1])

    # Attach both parts
    htmlpart = MIMEText(html, 'html', 'UTF-8')
    msg.attach(htmlpart)

    # Create a generator and flatten message object to 'file’
    str_io = StringIO()
    g = Generator(str_io, False)
    g.flatten(msg)
    # str_io.getvalue() contains ready to sent message

    try:
        smtp = smtplib.SMTP(smtpserver,587)
        smtp.login(smtp_username,smtp_password)
        smtp.sendmail(from_address[1], recipient[1], str_io.getvalue())
        print "Successfully sent email"
    except SMTPException:
        print "Error: unable to send email"



# MAIN PROGRAM     
def main():
    ########################
    # Get command line parameters (GetOpt)
    ########################
    check_given_cmd_params = 0 # 1 check for each argument = 3 (1+1+1=3)
    try:
        opts, args = getopt.getopt(sys.argv[1:], "hr:n:s:", ["help", "recipient-mail-addr=", "recipient-name=", "savetv-movie-list="])
    except getopt.GetoptError as err:
        # print help information and exit:
        print(err) # will print something like "option -a not recognized"
        print "Usage: --recipient-mail-addr=<test@example.com> --recipient-name=<username> --savetv-movie-list=<movie-liste.txt>"
        sys.exit(2)
    for o, a in opts:
        if o in ("-h", "--help"):
            print "Usage: --recipient-mail-addr=<test@example.com> --recipient-name=<username> --savetv-movie-list=<movie-liste.txt>"
            sys.exit()
        elif o in ("-r", "--recipient-mail-addr"):
            recipient[1] = a
            check_given_cmd_params = check_given_cmd_params + 1
        elif o in ("-n", "--recipient-name"):
            recipient[0] = a
            check_given_cmd_params = check_given_cmd_params + 1
        elif o in ("-s", "--savetv-movie-list"):
            movielist_filename = a
            check_given_cmd_params = check_given_cmd_params + 1
        else:
            assert False, "unhandled option"

    if check_given_cmd_params != 3:
        print "Usage: --recipient-mail-addr=<test@example.com> --recipient-name=<username> --savetv-movie-list=<movie-liste.txt>"
        sys.exit(2)

    #######################
    # Init
    #######################
    # SQLite DB Filenames
    db_savetv = recipient[0].lower() + "/savetvRecordings.db"
    db_filename = recipient[0].lower() + "/epgEventsMatched.db"
    db_backup_filename = recipient[0].lower() + "/epgEventsMatched.backup.db"
    db_swap_filename = recipient[0].lower() + "/epgEventsMatched.swap.db"

    #######################
    # Begin the logic
    #######################
    # Connect to TVheadend Server
    client_savetv = connect_savetv_server(savetv_username, savetv_password)

    # Connect and init new DBs
    con_savetv_db = init_and_connect_savetv_recordings_DB(db_savetv)
    con_matched_results_db = init_and_connect_matched_results_DB(db_filename)

    # Fetch SaveTV recordings and store in database
    savetv_fetch_movies(client_savetv, con_savetv_db)

    # 1) Search in EPG for movies and write to database (only in case of matches!)
    match_fileEntries_with_saveTV_recordings(movielist_filename, con_savetv_db, con_matched_results_db)

    # 2) Add movies with IMDB >= 8
    add_great_imdb_rated_movies(con_savetv_db, con_matched_results_db,rating=7)

    # Check if there were any matches or updates
    # Open old state of DB and delete (old) already transferred matches
    if (checkUpdates(con_matched_results_db, db_backup_filename, db_filename)):
        # Search for matching titles
        htmlmsg = query_and_generate_HTML_from_DB(con_matched_results_db)

        # Send Mail
        sendMail(htmlmsg, from_address, recipient, subject)
    else:
        print("[*] No new movies found ... not sending an email")

    # Disconnect
    disconnectDB(con_savetv_db)
    disconnectDB(con_matched_results_db)


if __name__ == "__main__":
    main()
