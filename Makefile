test :
	py.test tut_tests.py -n 1

docs:
	cd doc && $(MAKE) html
	cp -r doc/build/html/* tutorial/static/doc

alltest :
	py.test tut_tests.py -n 1
	py.test tut_gps_tests.py

publish :
	rsync -ar -e ssh tutorial thingotr@thingotron.com:marion
	rsync -ar -e ssh biblio thingotr@thingotron.com:marion
	rsync -a -e ssh *.py thingotr@thingotron.com:marion
	rsync -a -e ssh english_stop.txt thingotr@thingotron.com:marion
#rsync -a -e ssh csv_to_citation_timestamp.py thingotr@thingotron.com:dev/citation_query
#	rsync -a -e ssh feed_graphite.py thingotr@thingotron.com:dev/citation_query
#	rsync -a -e ssh test_citation_query.csv thingotr@thingotron.com:dev/citation_query
	ssh -t thingotr@thingotron.com "cd /home3/thingotr/marion && sed -i s/debug=True/debug=False/g local_conf.py"

publish_db :
	rsync -a -e ssh app.db thingotr@thingotron.com:marion

publish_storage :
	rsync -ar -e ssh user_storage thingotr@thingotron.com:marion

publish_all : publish publish_db publish_storage
