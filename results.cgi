#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sqlite3 as lite
import re
import cgi, cgitb
import os, platform
from helper import wrap, lemma_exists, get_lemmas_for_word
from helper import separate_coptic
from operator import itemgetter
cgitb.enable()

print "Content-type: text/html\n"

	
def first_orth(orthstring):
	first_orth = re.search(r'\n(.*?)~', orthstring)
	if first_orth is not None:
		return first_orth.group(1)
	else:
		return "NONE"

def second_orth(orthstring):
	first_search = re.search(r'\n(.*?)~', orthstring)
	if first_search is not None:
		first = first_search.group(1)
	else:
		first = ""

	second_orth = re.search(r'\n(.*?)[^\n]*\n(.*?)~', orthstring)
	sub_entries = re.findall(r'\n(.*?)~', orthstring)
	distinct_entries = set([])
	for entry in sub_entries:
		if entry.encode("utf8") != first.encode("utf8"):
			distinct_entries.add(entry)
	count_sub_entries = len(distinct_entries)
	dots = ", ..." if count_sub_entries > 2 else ""

	if second_orth is not None:
		if second_orth.group(2) != first:
			return second_orth.group(2) + dots
	return "--"


def sense_list(sense_string):
	senses = sense_string.split("|||")
	sense_html = '<ol class="sense_list">'
	for sense in senses:
		definition = re.search(r'~~~(.*);;;', sense)
		if definition is not None:
			sense_html += "<li>" + definition.group(1).encode("utf8") + "</li>"
	sense_html += "</ol>"
	return sense_html
		

def retrieve_entries(word, dialect, pos, definition, def_search_type, def_lang):
	sql_command = 'SELECT * FROM entries WHERE '
	constraints = []
	parameters = []

	#what's in the 'Search' column--based on word, word_search_type, dialect
	if len(word) > 0:
		if dialect == 'any':
			word_search_string = r'.*\n' + word + r'~.*'
		else:
			word_search_string = r'.*\n' + word + r'~' + dialect + r'?\n.*'

		word_constraint = "entries.search REGEXP ?"
		constraints.append(word_constraint)
		parameters.append(word_search_string)
		
	elif dialect != 'any':
		dialect_constraint = "entries.search REGEXP ?"
		constraints.append(dialect_constraint)
		parameters.append(r'.*~' + dialect + r'?\n')

	# POS column, based on pos
	if pos != 'any':
		pos_constraint = "entries.POS = ?"
		constraints.append(pos_constraint)
		parameters.append(pos)

	# one or all of the sense columns--which is specified by def_lang, search within it based on definition and def_search_type
	if def_search_type == 'exact sequence':
		def_search_string = r'.*\b' + definition + r'\b.*'
		if def_lang == 'any':
			def_constraint = "(entries.en REGEXP ? OR entries.de REGEXP ? OR entries.fr REGEXP ?)"
			constraints.append(def_constraint)
			parameters.append(def_search_string)
			parameters.append(def_search_string)
			parameters.append(def_search_string)
		elif def_lang == 'en':
			def_constraint = "entries.en REGEXP ?"
			constraints.append(def_constraint)
			parameters.append(def_search_string)
		elif def_lang == 'fr':
			def_constraint = "entries.fr REGEXP ?"
			constraints.append(def_constraint)
			parameters.append(def_search_string)
		elif def_lang == 'de':
			def_constraint = "entries.de REGEXP ?"
			constraints.append(def_constraint)
			parameters.append(def_search_string)

	elif def_search_type == 'all words':
		words = definition.split(' ')
		for one_word in words:
			def_search_string = r'.*\b' + one_word + r'\b.*'
			if def_lang == 'any':
				def_constraint = "(entries.en REGEXP ? OR entries.de REGEXP ? OR entries.fr REGEXP ?)"
				constraints.append(def_constraint)
				parameters.append(def_search_string)
				parameters.append(def_search_string)
				parameters.append(def_search_string)
			elif def_lang == 'en':
				def_constraint = "entries.en REGEXP ?"
				constraints.append(def_constraint)
				parameters.append(def_search_string)
			elif def_lang == 'fr':
				def_constraint = "entries.fr REGEXP ?"
				constraints.append(def_constraint)
				parameters.append(def_search_string)
			elif def_lang == 'de':
				def_constraint = "entries.de REGEXP ?"
				constraints.append(def_constraint)
				parameters.append(def_search_string)

	sql_command += " AND ".join(constraints)
	sql_command += " ORDER BY ascii"

	if platform.system() == 'Linux':
		con = lite.connect('alpha_kyima_rc1.db')
	else:
		con = lite.connect('coptic-dictionary' + os.sep + 'alpha_kyima_rc1.db')

	con.create_function("REGEXP", 2, lambda expr, item : re.search(expr.lower(), item.lower()) is not None)
	with con:
		cur = con.cursor()
		cur.execute(sql_command, parameters)
		rows = cur.fetchall()

		if len(rows) == 1:
			row = rows[0]
			entry_url = "entry.cgi?entry=" + str(row[0]) + "&super=" + str(row[1])
			#return '<meta http-equiv="refresh" content="0; URL="' + entry_url + '" />'
			return '<script>window.location = "' + entry_url + '";</script>'
		elif len(rows) > 100:
			tablestring = '<div class="content">\nSearch had ' + str(len(rows)) + ' results - showing first 100'
			rows = rows[:100]
		elif len(rows) == 0 and len(word) > 0:  # no matches found
			tablestring = '<div class="content">\n' + str(len(rows)) + ' results for <span class="anti">' + word.encode("utf8") + "</span>\n"
			if lemma_exists(word.encode("utf8")):
				tablestring += "<br/>This may be a form of:<br/>\n"
				tablestring += '<table id="results" class="entrylist">'
				rows = get_lemmas_for_word(word)
				for row in rows:
					tablestring += "<tr>"

					orth = row[0]
					link = "results.cgi?coptic=" + row[0]
					lem_pos = str(row[1])
					#print lem_pos

					tablestring += '<td class="orth_cell">' + '<a href="' + link.encode("utf8") + '">'
					tablestring += orth.encode("utf8")
					tablestring += "</a>" + "</td>"
					tablestring += '<td class="pos_cell">' + '(for '+word +'/' + lem_pos + ')</td>'

					tablestring += "</tr>"
				tablestring += "</table>\n</div>\n"
				return tablestring
		else:
			tablestring = '<div class="content">\n' + str(len(rows)) + ' Results'
		tablestring += '<table id="results" class="entrylist">'
		for row in rows:
			tablestring += "<tr>"
			
			orth = first_orth(row[2])
			second = second_orth(row[2])
			link = "entry.cgi?entry=" + str(row[0]) + "&super=" + str(row[1])
			
			tablestring += '<td class="orth_cell">' + '<a href="' + link + '">' + orth.encode("utf8") + "</a>" +"</td>"
			tablestring += '<td class="second_orth_cell">' +  second.encode("utf8")  +"</td>"
			
			sense = sense_list(row[5])
			tablestring += '<td class="sense_cell">' + sense + "</td>"
			
			tablestring += "</tr>"
		tablestring += "</table>\n</div>\n"
		return tablestring
					
			
if __name__ == "__main__":
	form = cgi.FieldStorage()
	word = form.getvalue("coptic", "")
	dialect = form.getvalue("dialect", "any")
	pos = form.getvalue("pos", "any")
	definition = form.getvalue("definition", "")
	def_search_type = form.getvalue("def_search_type", "exact sequence")
	def_lang = form.getvalue("lang", "any")
	quick_string = form.getvalue("quick_search", "")
	if quick_string != "":
		separated = separate_coptic(quick_string)
		def_search_type = "all words"
		word = " ".join(separated[0])
		definition = " ".join(separated[1])
		
	word = word.decode("utf8")
	results_page = retrieve_entries(word, dialect, pos, definition, def_search_type, def_lang)
	wrapped = wrap(results_page)
	print wrapped