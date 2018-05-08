#!/usr/bin/env python
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
output_file = '/home/download/puntate_test'
exception_list = {
    'Castle': ['Castle.2009'],
    'Tomorrow.People': ['Tomorrow.People.US'],
    'House.of.Cards':
    ['House.of.Cards.2013', 'house.of.cards.2013', 'house.of.cards'],
    'The.Flash.2014': ['The.flash', 'the.flash.2014', 'The.Flash'],
    'Shameless.US': ['Shameless', 'shameless.us'],
    'The.Blacklist': ['the.blacklist'],
    'Greys.Anatomy': ['greys.anatomy'], 'Games.of.Thrones': ['games.of.thrones'],
    'Better.Call.Saul': ['Better.Call.Saul.US'],
    'The.Librarians': ['The.Librarians.US'],
    'Riverdale.US': ['Riverdale'],
    'Siren.2018': ['Siren', 'siren.2018'],
    'The.Last.Ship': ['the.last.ship'],
    'The.Originals': ['the.originals'],
    'Gotham': ['gotham'],
    'Supernatural': ['supernatural'],
    'Charmed': ['Charmed.2018', 'charmed.2018'],
    'Criminal.Minds': ['criminal.minds'],
    'Call.the.Midwife': ['call.the.midwife', 'call_the_midwife'],
    'DCs.Legends.of.Tomorrow': ['dcs.legends.of.tomorrow', 'DCs.Legends.Of.Tomorrow'],
    'American.Horror.Story': ['american.horror.story'],
    'Legacies': ['legacies'],
    'Young.Sheldon': ['young.sheldon'],
    'Batwoman': ['batwoman'],
}
excluded_ext = ['nfo', 'txt', 'jpg']
video_ext = ['mkv']
subs_ext = ['srt']
regexp = re.compile(r"(.*)\.S([0-9]+?)E([0-9]+?|[0-9]+?\-[0-9]+?)\.(.*)", re.I)

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
    for _, exception in exception_list.items():
        if filename in exception:
            tv_serie_name = exception_list.keys()[
                exception_list.values().index(exception)]
            j = i.replace(filename, tv_serie_name)
            shutil.move(dest + '/' + i, dest + '/' + j)
            i = j
            normalized = normalized.replace(filename, tv_serie_name)
    return normalized, i


def scan_dirs(dest, dict_subs={}):
    temp_dict = dict()
    del_list = list()
    for i in os.listdir(dest):
        result = regexp.match(i)
        if result and not os.path.isdir(
                dest + '/' + i) and result.group(4)[
                -3:] in video_ext:
            normalized, normalized_sub = normalize_file(result, i, dest)
            temp_dict[normalized.lower()] = dest + '/' + normalized_sub
        elif result and os.path.isdir(dest + '/' + i):
            del_list.append(dest + '/' + i)
            (y, _, dict_subs) = scan_dirs(dest + '/' + i, dict_subs)
            temp_dict.update(y)
        elif result and not os.path.isdir(dest + '/' + i) and result.group(4)[-3:] in subs_ext:
            normalized, normalized_sub = normalize_file(result, i, dest)
            if normalized_sub not in dict_subs:
                dict_subs[normalized.lower()] = dest + '/' + normalized_sub
    return temp_dict, del_list, dict_subs


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
            if key in local_config["telegram"] and local_config["telegram"][
                    key]:
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
    pretty = Formatter()
    overrided_config = check_config(config, local_config, args)
    LOGGER.debug("""
-------------------------------------
DUMP CONFIG
-------------------------------------
%s""" % pretty(overrided_config.__dict__))
    bot = telepot.Bot(overrided_config["telegram"]["bot_key"])
    (dict_subs, _, dict_subs) = scan_dirs(dir_subs)
    (dict_files, del_list, dict_subs) = scan_dirs(dir_files, dict_subs)
    to_move = set(dict_files.keys()).intersection(set(dict_subs.keys()))
    out_file = open(output_file, 'a')
    LOGGER.debug("""
-------------------------------------
DUMP VARIABLES
-------------------------------------
to_move:
%s
list subs:
%s
list files:
%s
del list:
%s
""" % (pretty(to_move), pretty(dict_subs), pretty(dict_files), pretty(del_list)))
    for episode in to_move:
        videofile = dict_files[episode]
        if dict_subs[episode].split('.')[-1] == 'zip':
            sub = zipfile.ZipFile(dict_subs[episode])
            sub_extracted = sub.extract(sub.namelist()[0], '/tmp')
        else:
            sub_extracted = dict_subs[episode]
        destination = dir_dest + '/' + regexp.match(dict_files[episode].split(
            '/')[-1]).group(1).replace('.', ' ') + '/Season ' + episode.split('.')[-2]
        mkdir_p(destination)
        shutil.move(sub_extracted, destination + '/' + '.'.join(videofile.split('/')
                                                                [-1].split('.')[:-1]) + '.' + sub_extracted.split('.')[-1])
        LOGGER.debug("shutil.move(%s, %s/%s)\n" %
                     (videofile, destination, videofile.split('/')[-1]))
        shutil.move(videofile, destination + '/' + videofile.split('/')[-1])
        try:
            os.chmod(destination + '/' + videofile.split('/')[-1], 660)
            os.chmod(destination, 2770)
        except OSError:
            print("Can't change permissions, different owner")
        output_string = "PUNTATA COPIATA: %s\n" % videofile
        out_file.write(output_string)
        LOGGER.info(output_string)
        try:
            bot.sendMessage(
                overrided_config["telegram"]["target"],
                "PUNTATA COPIATA: %s\n" % videofile)
        except Exception:
            pass
        if os.path.dirname(videofile) in del_list:
            LOGGER.debug("shutil.rmtree(%s)\n" % os.path.dirname(videofile))
            shutil.rmtree(os.path.dirname(videofile))
    out_file.close()


if __name__ == "__main__":
    setup_logging()
    main()
