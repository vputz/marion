test :
	nosetests tut_tests.py

#publish :
#rsync -a -e ssh citation_query.py thingotr@thingotron.com:dev/citation_query
#rsync -a -e ssh csv_to_citation_timestamp.py thingotr@thingotron.com:dev/citation_query
#	rsync -a -e ssh feed_graphite.py thingotr@thingotron.com:dev/citation_query
#	rsync -a -e ssh test_citation_query.csv thingotr@thingotron.com:dev/citation_query
