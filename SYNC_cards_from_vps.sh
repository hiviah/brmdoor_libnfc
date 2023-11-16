#!/bin/bash

# This copies 2 files, cards.txt and cards_desfire.txt from brmdoor@brmlab.cz
# Shows the mtime (modified time according to server), which should be set to:
#
# $ cat /etc/timezone 
# Europe/Prague
#
# Use same timezones, you'll have less headache
# The mtime check is just a sanity check, a human should check if it's correct
#
# ANY TIME YOU CAN ABORT THE SCRIPT WITH CTRL-C, BUT DABASE CHANGES THAT HAPPENED
# WILL NOT ROLL BACK!
#
# Then it will show diff of cards existing and to be imported in vimdiff
# Overview and use !q to exit
#
# Script will ask 3 times, Enter is accept, Ctrl-C is abort:
# 1) do you agree with the mtimes, are they corre



################################################################
# Settings - keys, user, server
#

USERNAME=brmdoor
SERVER=brmlab.cz
SSH_PRIVATE_KEY="$HOME/.ssh/brmdoor_vps_ecdsa-sha2-nistp256"
BRMDOOR_SQLITE_DB="$HOME/brmdoor_libnfc/brmdoor.sqlite"
WORK_DIR="$HOME/brmdoor_libnfc/"


################################################################
# Trapping errors
#

tempfiles=( )
cleanup() {
  rm -f "${tempfiles[@]}"
}
trap cleanup 0

error() {
  local parent_lineno="$1"
  local message="$2"
  local code="${3:-1}"
  if [[ -n "$message" ]] ; then
    echo "Error on or near line ${parent_lineno}: ${message}; exiting with status ${code}"
  else
    echo "Error on or near line ${parent_lineno}; exiting with status ${code}"
  fi
  exit "${code}"
}
trap 'error ${LINENO}' ERR

# This shit doesn't work on SQLite, but works on 'sort'
export LC_ALL=C.UTF-8


################################################################
# Actual code that downloads cards, shows diff, asks if you agree.
# If agreed, cards will be imported into brmdoor db

BLUE='\033[0;34m'
WHITE='\033[0;37m' 
RED='\033[0;31m'


clear


echo -e "$RED"
echo "################## READ THE DIRECTIONS FFS! #######################"
echo "---!--- We are going to download cards files from $USERNAME@$SERVER, we will show you first the last modified time (mtime) as a sanity check"
echo "---!--- Entering work directory $WORK_DIR"
echo -e "$WHITE"
cd "$WORK_DIR"

# Following will work with config, but we are using variables set here
#sftp brmdoor@brmlab.cz <<< "ls -l cards/"

sftp -i "$SSH_PRIVATE_KEY" "$USERNAME@$SERVER" <<< "ls -l cards/" || error "SFTP file list failed"



echo -e "$RED"
echo
echo
echo "--???-- Do you accept the last modified time of changes?"
echo "---!--- Press ENTER to continue or CTRL-C to ABORT"
read

echo -e "$WHITE"
sftp -i "$SSH_PRIVATE_KEY" "$USERNAME@$SERVER":cards/"cards*.txt" . || error "SFTP file card download failed"

echo -e "$RED"
echo "---!--- Accepted, downloaded 2 files, for UID cards and Desfire cards."
echo "---!--- Now we will show differences in vimdiff for UID-only cards first, use :qa! to quit vimdiff or zR to expand complete file, then answer whether you accept changes"
echo "---!--- Note there a tiny bug in 'sort' vs SQL collate, some members may appear at different order in list"
echo "---!--- Press ENTER to continue or CTRL-C to ABORT"
read



NEW_CARDS_FILE="cards.txt"
vimdiff <(sqlite3 "$BRMDOOR_SQLITE_DB" 'select nick, uid_hex from authorized_uids order by nick,uid_hex COLLATE RTRIM;') <(LC_ALL=C sort <"$NEW_CARDS_FILE" | sed 's/ /|/')

echo -e "$BLUE"
echo "---!--- Now you have seen difference for UID-based cards"
echo -e "$RED"
echo "---!--- Do you accept changes?"
echo "---!--- Press ENTER to continue or CTRL-C to ABORT"
read

echo -e "$RED"
echo "---!--- We will show differences for *****DESFIRE***** cards, use :qa! to quit vimdiff or zR to expand complete file"
echo "---!--- Press ENTER to continue or CTRL-C to ABORT"
read

NEW_CARDS_FILE="cards_desfire.txt"
vimdiff <(sqlite3 ~/brmdoor_libnfc/brmdoor.sqlite 'select nick, uid_hex from authorized_desfires order by nick,uid_hex;') <(LC_ALL=C sort <"$NEW_CARDS_FILE" | sed 's/ /|/')

echo -e "$BLUE"
echo "---!--- Now you have seen difference for DESFIRE-based cards"
echo -e "$RED"
echo "---!--- Do you accept changes?"
echo "---!--- Press ENTER to continue or CTRL-C to ABORT"
echo
echo "Now ALL ACCEPTED CHANGES WILL BE COMMITED to brmdoor DB on Enter"

read

python2 ./import_jendasap_cards.py cards.txt brmdoor.sqlite && \
    echo "Imported UID-based cards" && \
    ./import_jendasap_cards.py --desfire cards_desfire.txt brmdoor.sqlite || \
    error "Full import failed, check what got b0rked"
