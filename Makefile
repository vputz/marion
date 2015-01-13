test :
	nosetests tut_tests.py

publish :
	rsync -ar -e ssh tutorial thingotr@thingotron.com:marion
	rsync -ar -e ssh biblio thingotr@thingotron.com:marion
	rsync -a -e ssh *.py thingotr@thingotron.com:marion
	rsync -a -e ssh english_stop.txt thingotr@thingotron.com:marion
#rsync -a -e ssh csv_to_citation_timestamp.py thingotr@thingotron.com:dev/citation_query
#	rsync -a -e ssh feed_graphite.py thingotr@thingotron.com:dev/citation_query
#	rsync -a -e ssh test_citation_query.csv thingotr@thingotron.com:dev/citation_query

publish_db :
	rsync -a -e ssh app.db thingotr@thingotron.com:marion

publish_storage :
	rsync -ar -e ssh user_storage thingotr@thingotron.com:marion

publish_all : publish publish_db publish_storage
