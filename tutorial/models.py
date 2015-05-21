import json
from flask import current_app
from flask.ext.security import UserMixin, RoleMixin
import os
import werkzeug
from flask.ext.sqlalchemy import SQLAlchemy
from datetime import datetime
from biblio.wos_reader import open_wos_tab, make_pytable
from biblio.wos_reader_query import run_query
from biblio import csv_queries
import csv

db = SQLAlchemy()

roles_users = db.Table(
    'roles_users',
    db.Column('id_user', db.Integer(), db.ForeignKey('user.id')),
    db.Column('id_role', db.Integer(), db.ForeignKey('role.id')))


class Role(db.Model, RoleMixin):
    id = db.Column(db.Integer(), primary_key=True)
    name = db.Column(db. String(64), unique=True)
    description = db.Column(db.String(255))


class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    nickname = db.Column(db.String(64), index=True, unique=True)
    email = db.Column(db.String(128), index=True, unique=True)
    password = db.Column(db.String(255))
    active = db.Column(db.Boolean())
    confirmed_at = db.Column(db.DateTime())
    roles = db.relationship(
        'Role', secondary=roles_users,
        backref=db. backref('users', lazy='dynamic'))
    datasets = db.relationship("Dataset", backref='owner', lazy='dynamic')
    tabdata_datasets = db.relationship("Tabdata_dataset", backref='owner',
                                       lazy='dynamic')

    def storage_path(self):
        return os.path.join(current_app.config['STORAGE_BASEDIR'],
                            'user_'+str(self.id))

    def is_authenticated(self):
        return True

    def is_active(self):
        return True

    def is_anonymous(self):
        return False

    def get_id(self):
        try:
            return unicode(self.id)
        except NameError:
            return str(self.id)

    def __repr__(self):
        return '<User %r (%r)>' % (self.nickname, self.email)

    def add_file(self, werkzeug_file):
        filename = werkzeug.secure_filename(werkzeug_file.filename)
        if not os.path.exists(self.storage_path()):
            os.makedirs(self.storage_path())
        werkzeug_file.save(os.path.join(self.storage_path(), filename))

    def add_dataset(self, description, query_text):
        new_set = Dataset(description=description,
                          query_text=query_text,
                          owner=self,
                          date_created=datetime.utcnow())
        db.session.add(new_set)
        db.session.commit()

    def add_tabdata_dataset(self, description, werkzeug_file):
        """

        Arguments:
        - `self`:
        - `description`: short description
        - `werkzeug_file`: file for upload; this can be blank,
           but that will be awkward
        """
        new_set = Tabdata_dataset(description=description, owner=self,
                                  date_created=datetime.utcnow())
        db.session.add(new_set)
        db.session.commit()
        new_set.add_csv(werkzeug_file)
        return new_set


class Dataset(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    id_user = db.Column(db.Integer, db.ForeignKey('user.id'))
    description = db.Column(db.String(255))
    query_text = db.Column(db.String(1024))
    date_created = db.Column(db.DateTime())
    csv_files = db.relationship("Csv_fileref",
                                backref="dataset", lazy='dynamic')
    h5_files = db.relationship("H5_fileref",
                               backref="dataset", lazy='dynamic')
    query_instances = db.relationship("Query_instance",
                                      backref="dataset", lazy="dynamic")

    def tab_storage_path(self):
        return os.path.join(self.owner.storage_path(),
                            'dataset_'+str(self.id), 'tabs')

    def h5_storage_path(self):
        return os.path.join(self.owner.storage_path(),
                            'dataset_'+str(self.id))

    def query_result_storage_path(self):
        return os.path.join(self.owner.storage_path(),
                            'dataset_'+str(self.id), 'queries')

    def add_csv(self, werkzeug_file):
        fileref = Csv_fileref(dataset=self,
                              filename=werkzeug_file.filename)
        db.session.add(fileref)
        db.session.commit()
        if not os.path.exists(self.tab_storage_path()):
            os.makedirs(self.tab_storage_path())
        werkzeug_file.save(fileref.stored_fullpath())

    def add_query_instance(self, query_id):
        q = Query.query.get(query_id)
        qi = Query_instance(dataset=self, query_def=q)
        db.session.add(qi)
        db.session.commit()

    def regenerate_h5_file(self):
        if len(list(self.h5_files)) == 0:
            h5 = H5_fileref(dataset=self)
            db.session.add(h5)
            db.session.commit()
        else:
            h5 = self.h5_files[0]
        tabfiles = [tab.stored_fullpath() for tab in self.csv_files]
        with open_wos_tab(tabfiles) as wos:
            make_pytable(wos, h5.stored_fullpath(), self.description)

    def delete_missing_filerefs(self):
        # delete missing tabfiles
        csvfiles = list(self.csv_files)
        for tab in csvfiles:
            if not os.path.isfile(tab.stored_fullpath()):
                db.session.delete(tab)
                db.session.commit()

        # now same for h5
        h5files = list(self.h5_files)
        for h5 in h5files:
            if not os.path.isfile(h5.stored_fullpath()):
                db.session.delete(h5)
                db.session.commit()

    def h5_date(self):
        if len(list(self.h5_files)) == 0:
            return None
        h5 = self.h5_files[0]
        return os.path.getmtime(h5.stored_fullpath())

    def h5_file(self):
        if len(list(self.h5_files)) > 0:
            return self.h5_files[0]
        else:
            return None

    def h5_file_is_up_to_date(self):
        self.delete_missing_filerefs()

        h5_date = self.h5_date()
        if h5_date is None:
            return False

        if len(list(self.h5_files)) == 1:
            for csv_file in self.csv_files:
                # TODO trouble if files are wedged
                csv_date = os.path.getmtime(csv_file.stored_fullpath())
                if csv_date > h5_date:
                    return False
        return True


class Csv_fileref(db.Model):
    id = db.Column(db.Integer(), primary_key=True)
    id_dataset = db.Column(db.Integer, db.ForeignKey('dataset.id'))
    filename = db.Column(db.String(1024))

    def stored_filename(self):
        return "tab_" + str(self.id)

    def stored_fullpath(self):
        return os.path.join(self.dataset.tab_storage_path(),
                            self.stored_filename())


class H5_fileref(db.Model):
    id = db.Column(db.Integer(), primary_key=True)
    id_dataset = db.Column(db.Integer, db.ForeignKey('dataset.id'))
    filename = db.Column(db.String(1024))

    def stored_filename(self):
        return "h5_"+str(self.id)

    def stored_fullpath(self):
        return os.path.join(self.dataset.h5_storage_path(),
                            self.stored_filename())


class Query(db.Model):
    id = db.Column(db.Integer(), primary_key=True)
    name = db.Column(db.String(255))
    description = db.Column(db.String(1024))
    filename = db.Column(db.String(1024))
    template = db.Column(db.String(1024))

    def query_basepath(self):
        return current_app.config['QUERIES_BASEDIR']

    def stored_query_fullpath(self):
        return os.path.join(self.query_basepath(), self.filename)


class Gps_remap(db.Model):
    __bind_key__ = 'gps_cache'
    from_location = db.Column(db.String(255), primary_key=True)
    to_location = db.Column(db.String(128))


class Gps_cache(db.Model):
    __bind_key__ = 'gps_cache'
    location = db.Column(db.String(255), primary_key=True)
    latitude = db.Column(db.Float(32))
    longitude = db.Column(db.Float(32))

# this is put down here to avoid circular import difficulties
from tutorial.geocache import get_locations_and_unknowns, get_location


class Query_instance(db.Model):
    id = db.Column(db.Integer(), primary_key=True)
    id_dataset = db.Column(db.Integer, db.ForeignKey('dataset.id'))
    id_query = db.Column(db.Integer, db.ForeignKey('query.id'))

    query_def = db.relationship("Query")

    def is_current(self):
        """does the query have the same or later date as the h5 file?"""
        if not os.path.exists(self.stored_fullpath()):
            return False
        h5_date = self.dataset.h5_date()
        query_result_date = os.path.getmtime(self.stored_fullpath())
        return query_result_date >= h5_date

    def render_query(self):
        if not os.path.exists(self.dataset.query_result_storage_path()):
            os.makedirs(self.dataset.query_result_storage_path())
        print(self.query_def.stored_query_fullpath())
        run_query(
            self.stored_fullpath(),
            self.dataset.h5_file().stored_fullpath(),
            self.query_def.stored_query_fullpath(),
            {'paperLocationFunc': get_locations_and_unknowns})

    def retrieve_data(self):
        if not self.is_current():
            self.render_query()
        with open(self.stored_fullpath(), encoding='latin-1') as f:
            json_data = json.load(f)
        return json_data

    def stored_filename(self):
        return "query_"+str(self.id)

    def stored_fullpath(self):
        return os.path.join(self.dataset.query_result_storage_path(),
                            self.stored_filename())


class Tabdata_dataset(db.Model):
    """
    Incorporates the idea of a tabular dataset (csv, excel, etc).
    Initially this just supports CSV
    """

    id = db.Column(db.Integer(), primary_key=True)
    id_user = db.Column(db.Integer, db.ForeignKey('user.id'))
    description = db.Column(db.String(1024))
    date_created = db.Column(db.DateTime())
    query_instances = db.relationship("Tabdata_query_instance",
                                      backref="dataset", lazy="dynamic")

    def tab_storage_path(self):
        return os.path.join(self.owner.storage_path(),
                            'tab_dataset_'+str(self.id),
                            'tabs')

    def stored_filename(self):
        return "tab_" + str(self.id)

    def stored_fullpath(self):
        return os.path.join(self.tab_storage_path(), self.stored_filename())

    def add_csv(self, werkzeug_file):
        """
        Sets the file for this tab data.  This will overwrite the
        existing file and possibly invalidate the queries

        TODO: some verification of file (where to do this?)
        """
        if not os.path.exists(self.tab_storage_path()):
            os.makedirs(self.tab_storage_path())
        werkzeug_file.save(self.stored_fullpath())

    def column_choices(self):
        result = []
        with open(self.stored_fullpath()) as csvfile:
            reader = csv.reader(csvfile)
            row = next(reader)
            for i in range(len(row)):
                result.append((i, row[i]))
        return result

    def add_query_instance(self, tabdata_query_id, parameters):
        q = Tabdata_query.query.get(tabdata_query_id)
        qi = Tabdata_query_instance(dataset=self,
                                    query_def=q, parameters=parameters)
        db.session.add(qi)
        db.session.commit()


class Tabdata_query(db.Model):
    """
    A tab-data query.  Tabdata queries are somewhat simpler
    than full dataset queries as it is assumed
    that much of the data manipulation has been done already;
    as a result there is no "stored query text"
    but we do have a JSON dictionary "parameters" list which
    primarily will be used to select columns out
    of the csv file for various variables.
    """

    id = db.Column(db.Integer(), primary_key=True)
    name = db.Column(db.String(255))
    description = db.Column(db.String(1024))
    parameters = db.Column(db.String(2048))
    template = db.Column(db.String(1024))


class Tabdata_query_instance(db.Model):
    """
    The tab data query instance; contains a JSON dictionary in "parameters"
    matching the parameters of the query
    """
    id = db.Column(db.Integer(), primary_key=True)
    id_tabdata_dataset = db.Column(
        db.Integer,
        db.ForeignKey('tabdata_dataset.id'))
    id_tabdata_query = db.Column(db.Integer, db.ForeignKey('tabdata_query.id'))
    parameters = db.Column(db.String(2048))
    query_def = db.relationship("Tabdata_query")

    def retrieve_data(self):
        """
        Retrieve the data from the query, although in this case we shouldn't
        have to render data to a file; these should be fast queries (we hope)
        Arguments:
        - `self`:
        """
        # switch based on the name of the query--ugly, but for now we'll do it
        if self.query_def.name == "Tabdata_hexbin":
            json_data = csv_queries.location_and_value(
                self.dataset.stored_fullpath(), json.loads(self.parameters),
                get_location)
        elif self.query_def.name == "Tabdata_markercluster":
            json_data = csv_queries.location_and_value(
                self.dataset.stored_fullpath(), json.loads(self.parameters),
                get_location)
        else:
            json_data = "{}"
        return json_data
