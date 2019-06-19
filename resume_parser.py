#see \src\bash\resume_parser.sh for helper bash
#sys arg structure:
#-i <resumes directory>
#-p <space-separated primary keywords>
#-s <space-separated secondary keywords> 

# do they need sponsorship? 
# are they local?

import argparse
from tika import parser 
import spacy
import pandas as pd
from collections import Counter as cntr
import glob
import re
nlp = spacy.load('en_core_web_sm')

def parse_args():
	argparser = argparse.ArgumentParser(description='parse sysargs')
	argparser.add_argument('-i', '--indir', type = str, help = 'Relative input directory for resumes')
	argparser.add_argument('-p', '--primary', nargs = '+', help = 'List of must-have candidate skills. Ex: python SQL R', required = True)
	argparser.add_argument('-s', '--secondary', nargs = '+', help = 'List of nice-to-have candidate skills. Ex: scala excel', required = True)
	a = argparser.parse_args()
	return a.indir, a.primary, a.secondary

def cleanup(token):
	return token.lower().replace('\n','').strip()

def get_date_range(doc):
	dateEnts = [cleanup(e.string) for e in doc.ents if e.label_ == 'DATE'] 
	dateSplit = [[d for d in re.split(',|/|-| ',date)] for date in dateEnts]
	years = [d for sub in dateSplit for d in sub if d.isdigit() and int(d) > 1900 and int(d) < 2020]
	return int(max(years)) - int(min(years))

def get_common_words(doc, num):
	words = [cleanup(token.text) for token in doc if token.is_stop != True and 
		token.is_punct != True and '\n' not in token.text and not any(c in token.text for c in ['â','—','¦','|','ï','\n',' '])] 
	return cntr(words), ' '.join([x[0] for x in cntr(words).most_common(num)])

def get_common_nouns(doc, num):
	nouns = [cleanup(token.text) for token in doc if token.is_stop != True and 
		token.is_punct != True and token.pos_ == "NOUN" and not any(c in token.text for c in ['â','—','¦','|','ï','\n',' '])]
	return ' '.join([x[0] for x in cntr(nouns).most_common(num)])

def get_score(freq, primary, secondary):
	primary_scores = [4 + freq[w] if freq[w] > 0 else 0 for w in primary]
	secondary_scores = [0.5 + 0.5*freq[w] if freq[w] > 0 else 0 for w in secondary]
	return sum(primary_scores + secondary_scores)

def get_counts(freq, primary, secondary):
	keyword_cnt = [freq[w] for w in primary + secondary]
	has_all_pkw = ['N' if 0 in [freq[w] for w in primary] else 'Y']
	return keyword_cnt, has_all_pkw

def nlp_summary(indir, primary, secondary):
	summary = []
	for i, filepath in enumerate(glob.iglob('{}/*.pdf'.format(indir))):
		resume = parser.from_file(filepath)
		doc = nlp(resume['content'])
		yoe = get_date_range(doc) #get difference between oldest and newest mentioned years as approx. years of exp
		common_nouns = get_common_nouns(doc, 10) #get most common nouns (word blobs)
		word_freq, common_words = get_common_words(doc, 10) #get most common words, and frequency of all words
		keyword_count, has_all_pkw = get_counts(word_freq, primary, secondary) #get occurrence counts for all keywords
		score = get_score(word_freq, primary, secondary) #returns a score calculated from occurrence of primary and secondary keywords
		summary.append([filepath.rsplit('\\', 1)[-1], score, has_all_pkw[0], yoe] + keyword_count + [common_words, common_nouns])
	return summary

if __name__=='__main__':
	indir, primary, secondary = parse_args()
	summary = nlp_summary(indir, primary, secondary)
	df = pd.DataFrame(summary, columns=['Resume','Score','Has All Primary','Approx YOE'] + primary + secondary + ['Common Words', 'Common Nouns'])
	df = df.sort_values(by = 'Score', ascending = False)
	df.to_csv(indir + 'candidate_summaries.csv', index = False, encoding = 'utf-8')
	print(df[['Resume', 'Score', 'Has All Primary']])