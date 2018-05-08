#!/usr/bin/python
import errno, os, re, shutil, zipfile, telepot, argparse

class Formatter(object):
    def __init__(self):
        self.types = {}
        self.htchar = '\t'
        self.lfchar = '\n'
        self.indent = 0
        self.set_formater(object, self.__class__.format_object)
        self.set_formater(dict, self.__class__.format_dict)
        self.set_formater(list, self.__class__.format_list)
        self.set_formater(tuple, self.__class__.format_tuple)

    def set_formater(self, obj, callback):
        self.types[obj] = callback

    def __call__(self, value, **args):
        for key in args:
            setattr(self, key, args[key])
        formater = self.types[type(value) if type(value) in self.types else object]
        return formater(self, value, self.indent)

    def format_object(self, value, indent):
        return repr(value)

    def format_dict(self, value, indent):
        items = [
            self.lfchar + self.htchar * (indent + 1) + repr(key) + ': ' +
            (self.types[type(value[key]) if type(value[key]) in self.types else object])(self, value[key], indent + 1)
            for key in value
        ]
        return '{%s}' % (','.join(items) + self.lfchar + self.htchar * indent)

    def format_list(self, value, indent):
        items = [
            self.lfchar + self.htchar * (indent + 1) + (self.types[type(item) if type(item) in self.types else object])(self, item, indent + 1)
            for item in value
        ]
        return '[%s]' % (','.join(items) + self.lfchar + self.htchar * indent)

    def format_tuple(self, value, indent):
        items = [
            self.lfchar + self.htchar * (indent + 1) + (self.types[type(item) if type(item) in self.types else object])(self, item, indent + 1)
            for item in value
        ]
        return '(%s)' % (','.join(items) + self.lfchar + self.htchar * indent)

dir_subs = '/store/sata/subs'
dir_files = '/store/sata/torrent/downloads'
dir_dest = '/store/data/Telefilm'
output_file = '/home/download/puntate'
deb_file = '/home/download/debug_puntate'
exception_list = {'Castle.2009':'Castle','Tomorrow.People.US':'Tomorrow.People','House.of.Cards.2013':'House.of.Cards','house.of.cards.2013':'House.of.Cards','house.of.cards':'House.of.Cards','The.Flash':'The.Flash.2014', 'Shameless': 'Shameless.US','the.blacklist':'The.Blacklist','greys.anatomy':'Greys.Anatomy','the.flash':'The.Flash','games.of.thrones':'Games.of.Thrones','greys.anaomy':'Greys.Anatomy','Better.Call.Saul.US':'Better.Call.Saul','The.Librarians.US':'The.Librarians','Riverdale':'Riverdale.US','shameless.us':'Shameless.US'}
excluded_ext = ['nfo', 'txt', 'jpg']
debug_info = "true"
regexp = re.compile('(.*)\.S([0-9]{1,2})E([0-9]{1,2})\.(.*)', re.I)

def normalize_file(result, i, dest):
	normalized = '.'.join(result.group(1,2,3))
	filename = result.group(1)
	if exception_list.has_key(filename):
		j = i.replace(filename,exception_list[filename])
		shutil.move(dest+'/'+i,dest+'/'+j)
		i = j
		normalized = normalized.replace(filename,exception_list[filename])
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
			(x, y , _) = scan_dirs(dest + '/' + i)
			temp_list+=x
			temp_dict.update(y)
	return temp_list, temp_dict, del_list

def mkdir_p(path):
    try:
        os.makedirs(path)
    except OSError as exc: # Python >2.5
        if exc.errno == errno.EEXIST and os.path.isdir(path):
            pass
        else: raise

def main():
        parser = argparse.ArgumentParser()
        parser.add_argument('--bot_key', action='store', dest='bot_key', help='Telegram Bot Key')
        parser.add_argument('--target', action='store', dest='target_msg', help='Who will receive the messages')
        args = parser.parse_args()
        if args.bot_key and args.target_msg:
            bot = telepot.Bot(args.bot_key)
        ( subs_list, dict_subs, _ ) = scan_dirs(dir_subs)
	( files_list, dict_files, del_list ) = scan_dirs(dir_files, 1)
	pretty = Formatter()
	to_move = set(files_list).intersection(set(subs_list))
	out_file = open(output_file,'a')
	if debug_info == "true":
        	debug_file = open(deb_file,'a')
		debug_file.write("-------------------------------------\n")
		debug_file.write("DUMP VARIABLES\n")
		debug_file.write("-------------------------------------\n")
		debug_file.write("to_move:\n")
		debug_file.write(pretty(to_move))
		debug_file.write("\nlist subs:\n")
		debug_file.write(pretty(dict_subs))
		debug_file.write("\nlist files:\n")
		debug_file.write(pretty(dict_files))
		debug_file.write("\ndel list:\n")
		debug_file.write(pretty(del_list)+'\n')
	for episode in to_move:
		videofile = dict_files[episode]
		if dict_subs[episode].split('.')[-1] == 'zip':
			sub = zipfile.ZipFile(dict_subs[episode])
			sub_extracted = sub.extract(sub.namelist()[0],'/tmp')
		else:
			sub_extracted = dict_subs[episode]
		os.chmod(sub_extracted, 0660)
		destination = dir_dest+'/'+regexp.match(dict_files[episode].split('/')[-1]).group(1).replace('.',' ')+'/Season '+episode.split('.')[-2]
		mkdir_p(destination)
		shutil.move(sub_extracted, destination+'/'+'.'.join(videofile.split('/')[-1].split('.')[:-1])+'.'+sub_extracted.split('.')[-1])
		#os.chmod(destination+'/'+'.'.join(videofile.split('/')[-1].split('.')[:-1])+'.'+sub_extracted.split('.')[-1], 0660)
		if debug_info == "true":
			debug_file.write("shutil.move(%s, %s/%s)\n" % (videofile, destination, videofile.split('/')[-1]))
                shutil.move(videofile, destination+'/'+videofile.split('/')[-1])
		out_file.write("PUNTATA COPIATA: %s\n" % videofile)
                if args.bot_key and args.target_msg:
                    bot.sendMessage(args.target_msg, "PUNTATA COPIATA: %s\n" % videofile)
		if os.path.dirname(videofile) in del_list:
			if debug_info == "true":
				debug_file.write("shutil.rmtree(%s)\n" % os.path.dirname(videofile))
			shutil.rmtree(os.path.dirname(videofile))
	out_file.close()
	if debug_info == "true":
		debug_file.close()

if __name__ == "__main__":
	main()
