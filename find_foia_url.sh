#!/bin/bash

BASE_RECORD_URL="https://foiaonline.regulations.gov/foia/action/public/view/record?objectId="
BASE_REQUEST_URL="https://foiaonline.regulations.gov/foia/action/public/view/request?objectId="
BASE_OBJECT_ID="090004d280"
SUFFIX_LENGTH=6
SUCCESS_TEXT="tracking\snumber"
EXPECTED_ERROR_TEXT="DM_API_E_BADATTRNAME"
NON_PUBLIC_TEXT="The\sspecified\sitem\sis\snot\spublicly\sviewable."
SLEEP_SECONDS=.1
DATA_DIR="data"
GOOD_FILE_NAME="good.txt"
UNKNOWN_ERROR_FILE_NAME="error.txt"
NOT_PUBLIC_FILE_NAME="not_public.txt"

overwrite_files=false
base_dir=$(dirname "$0")
shard_prefix=""

for i in "$@"
do
case $i in
    --shard_prefix=*)
    shard_prefix="${i#*=}"
    shift # past argument=value
    ;;
    --overwrite)
    overwrite_files=True
    shift # past argument=value
    ;;
    *)
            # unknown option
    ;;
esac
done

shard_prefix_length=${#shard_prefix}
suffix_length=$((${SUFFIX_LENGTH} - ${shard_prefix_length}))
echo "Shard prefix: "$shard_prefix
echo "Shard prefix length; "$shard_prefix_length
echo "Suffix length: "$suffix_length

# This is a little terrible, we need to have a variable length for the brace expansion
# couldn't find a better way to do it.
case $suffix_length in
  1)
  suffixes=(${shard_prefix}{{0..9},{a..z}})
  ;;
  2)
  suffixes=(${shard_prefix}{{0..9},{a..z}}{{0..9},{a..z}})
  ;;
  3)
  suffixes=(${shard_prefix}{{0..9},{a..z}}{{0..9},{a..z}}{{0..9},{a..z}})
  ;;
  4)
  suffixes=(${shard_prefix}{{0..9},{a..z}}{{0..9},{a..z}}{{0..9},{a..z}}{{0..9},{a..z}})
  ;;
  5)
  suffixes=(${shard_prefix}{{0..9},{a..z}}{{0..9},{a..z}}{{0..9},{a..z}}{{0..9},{a..z}}{{0..9},{a..z}})
  ;;
  6)
  # shard_prefix should be empty here
  suffixes=(${shard_prefix}{{0..9},{a..z}}{{0..9},{a..z}}{{0..9},{a..z}}{{0..9},{a..z}}{{0..9},{a..z}}{{0..9},{a..z}})
  ;;
esac

if [ ! -d $base_dir/$DATA_DIR ]
  then mkdir $base_dir/$DATA_DIR
fi

if [ $overwrite_files = false ]
  then
  if [ -f $base_dir/$DATA_DIR/$GOOD_FILE_NAME ]
    then
    echo $GOOD_FILE_NAME" already exists! To overwrite specicy --overwrite true"
    exit 1
  fi
  if [ -f $base_dir/$DATA_DIR/$UNKNOWN_ERROR_FILE_NAME ]
    then
    echo $UNKNOWN_ERROR_FILE_NAME" already exists! To overwrite specicy --overwrite true"
    exit 1
  fi
  if [ -f $base_dir/$DATA_DIR/$NOT_PUBLIC_FILE_NAME ]
    then
    echo $NOT_PUBLIC_FILE_NAME" already exists! To overwrite specicy --overwrite true"
    exit 1
  fi
else
  echo "Possibly overwriting files!"
fi

count=0
for i in ${suffixes[*]}; do
  ((count++))
  sleep $SLEEP_SECONDS
  url=$BASE_RECORD_URL$BASE_OBJECT_ID$i
  result=$(curl --silent --fail $url)
  if [[ $(echo $result | grep -i $SUCCESS_TEXT) ]]
    then echo $url >> $base_dir/$DATA_DIR/$GOOD_FILE_NAME
  elif [[ $(echo $result | grep -i $NON_PUBLIC_TEXT) ]]
    then echo $url >> $base_dir/$DATA_DIR/$NOT_PUBLIC_FILE_NAME
  elif [[ ! $(echo $result | grep -i $EXPECTED_ERROR_TEXT) ]]
    then echo $url >> $base_dir/$DATA_DIR/$UNKNOWN_ERROR_FILE_NAME
  fi
done

echo $count" records processed"