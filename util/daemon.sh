#!/bin/sh
scriptpath="$1"
shift
action=$1
shift
extra_params=$@

if [ $(echo ${scriptpath} | head -c1) != '/' ]; then # this is already absolute path
	scriptpath="$(pwd)/$scriptpath"
fi

echo $scriptpath $extra_params
chmod +x $scriptpath

dirname="$(dirname ${scriptpath})"

filename="$(basename ${scriptpath})"
filename="${filename%.*}"

md5=$(echo ${scriptpath} | md5sum | cut -f1 -d' ')

sockname="/tmp/${filename}_${md5}.sock"
echo the daemon is using socket "$sockname"

zdaemon -p "$scriptpath" -z "$dirname" -s "$sockname" -d $action $extra_params
