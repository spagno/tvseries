#!/usr/bin/python
import argparse
import configparser
import errno
import json
import logging
import logging.config
import os
import re
import shutil
import sys
import zipfile
from formatter import Formatter

import telepot

dir_subs = '/store/sata/subs'
dir_files = '/store/sata/torrent/downloads'
dir_dest = '/store/data/Telefilm'
output_file = '/home/download/puntate'
exception_list = {'Castle.2009': 'Castle', 'Tomorrow.People.US': 'Tomorrow.People', 'House.of.Cards.2013': 'House.of.Cards', 'house.of.cards.2013': 'House.of.Cards', 'house.of.cards': 'House.of.Cards', 'The.Flash': 'The.Flash.2014', 'Shameless': 'Shameless.US', 'the.blacklist': 'The.Blacklist',
                  'greys.anatomy': 'Greys.Anatomy', 'the.flash': 'The.Flash', 'games.of.thrones': 'Games.of.Thrones', 'greys.anaomy': 'Greys.Anatomy', 'Better.Call.Saul.US': 'Better.Call.Saul', 'The.Librarians.US': 'The.Librarians', 'Riverdale': 'Riverdale.US', 'shameless.us': 'Shameless.US'}
excluded_ext = ['nfo', 'txt', 'jpg']
regexp = re.compile(r"(.*)\.S([0-9]{1,2})E([0-9]{1,2})\.(.*)", re.I)

LOGGER = logging.getLogger(__name__)

# thanks gionnyboy - https://github.com/gionniboy/howisresolved


def setup_logging(filepath="logging.json", log_level=logging.INFO):
    if not os.path.exists(filepath):
        LOGGER.error('no logging config file founded.')
        sys.exit('Create logging.json config file and restart.')

    with open(filepath, 'r') as fileconfig:
        config = json.load(fileconfig)
    logging.config.dictConfig(config)
    LOGGER.info('LOGGING SETUP from JSON %s', filepath)
    LOGGER.debug('LOGGING OK - path %s - level %s', filepath, log_level)


def normalize_file(result, i, dest):
    normalized = '.'.join(result.group(1, 2, 3))
    filename = result.group(1)
    if exception_list.has_key(filename):
        j = i.replace(filename, exception_list[filename])
        shutil.move(dest+'/'+i, dest+'/'+j)
        i = j
        normalized = normalized.replace(filename, exception_list[filename])
    return normalized, i


def scan_dirs(dest, isfiles=0):
    temp_dict = dict()
    temp_list = list()
    del_list = list()
    excluded_ext_large = excluded_ext
    if isfiles == 1:
        excluded_ext_large.append("srt")
    for i in os.listdir(dest):
        result = regexp.match(i)
        if result and result.group(4)[-4:] != 'part' and not os.path.isdir(dest + '/' + i) and result.group(4)[-3:] not in excluded_ext_large:
            normalized, normalized_sub = normalize_file(result, i, dest)
            temp_list.append(normalized.lower())
            temp_dict[normalized.lower()] = dest + '/' + normalized_sub
        elif result and os.path.isdir(dest + '/' + i):
            del_list.append(dest + '/' + i)
            (x, y, _) = scan_dirs(dest + '/' + i)
            temp_list += x
            temp_dict.update(y)
    return temp_list, temp_dict, del_list


def mkdir_p(path):
    try:
        os.makedirs(path)
    except OSError as exc:  # Python >2.5
        if exc.errno == errno.EEXIST and os.path.isdir(path):
            pass
        else:
            raise


def check_config(config, local_config, args):
    for key in config["telegram"]:
        if "telegram" in local_config.sections():
            if key in local_config["telegram"] and local_config["telegram"][key]:
                config["telegram"][key] = local_config["telegram"][key]
        if key in args.__dict__ and args.__dict__[key]:
            config["telegram"][key] = args.__dict__[key]
    return config


def main():
    config = configparser.ConfigParser()
    config.read('config.ini')
    local_config = configparser.ConfigParser()
    local_config.read('config.local.ini')
    parser = argparse.ArgumentParser()
    parser.add_argument('--bot_key', action='store',
                        dest='bot_key', help='Telegram Bot Key')
    parser.add_argument('--target', action='store',
                        dest='target', help='Who will receive the messages')
    args = parser.parse_args()
    overrided_config = check_config(config, local_config, args)
    bot = telepot.Bot(overrided_config["telegram"]["bot_key"])
    (subs_list, dict_subs, _) = scan_dirs(dir_subs)
    (files_list, dict_files, del_list) = scan_dirs(dir_files, 1)
    pretty = Formatter()
    to_move = set(files_list).intersection(set(subs_list))
    out_file = open(output_file, 'a')
    LOGGER.debug("-------------------------------------\n")
    LOGGER.debug("DUMP VARIABLES\n")
    LOGGER.debug("-------------------------------------\n")
    LOGGER.debug("to_move:\n")
    LOGGER.debug(pretty(to_move))
    LOGGER.debug("\nlist subs:\n")
    LOGGER.debug(pretty(dict_subs))
    LOGGER.debug("\nlist files:\n")
    LOGGER.debug(pretty(dict_files))
    LOGGER.debug("\ndel list:\n")
    LOGGER.debug(pretty(del_list)+'\n')
    for episode in to_move:
        videofile = dict_files[episode]
        if dict_subs[episode].split('.')[-1] == 'zip':
            sub = zipfile.ZipFile(dict_subs[episode])
            sub_extracted = sub.extract(sub.namelist()[0], '/tmp')
        else:
            sub_extracted = dict_subs[episode]
        os.chmod(sub_extracted, 0660)
        destination = dir_dest+'/'+regexp.match(dict_files[episode].split(
            '/')[-1]).group(1).replace('.', ' ')+'/Season '+episode.split('.')[-2]
        mkdir_p(destination)
        shutil.move(sub_extracted, destination+'/'+'.'.join(videofile.split('/')
                                                            [-1].split('.')[:-1])+'.'+sub_extracted.split('.')[-1])
        # os.chmod(destination+'/'+'.'.join(videofile.split('/')[-1].split('.')[:-1])+'.'+sub_extracted.split('.')[-1], 0660)
        LOGGER.debug("shutil.move(%s, %s/%s)\n" %
                     (videofile, destination, videofile.split('/')[-1]))
        shutil.move(videofile, destination+'/'+videofile.split('/')[-1])
        output_string = "PUNTATA COPIATA: %s\n" % videofile
        out_file.write(output_string)
        LOGGER.info(output_string)
        bot.sendMessage(
            overrided_config["telegram"]["target"], "PUNTATA COPIATA: %s\n" % videofile)
        if os.path.dirname(videofile) in del_list:
            LOGGER.debug("shutil.rmtree(%s)\n" % os.path.dirname(videofile))
            shutil.rmtree(os.path.dirname(videofile))
    out_file.close()


if __name__ == "__main__":
    setup_logging()
    main()
