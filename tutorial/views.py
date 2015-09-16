import os
import sys
from flask import render_template, flash, redirect
from flask import session, url_for, request, g
from flask import Blueprint
from flask import Response
from flask import copy_current_request_context
from flask.ext.login import login_user, logout_user, login_required
from flask.ext.security import current_user
from tutorial.forms import FileUploadForm, AddDatasetForm, \
     AddQueryToDatasetForm, MakeGpsRemapForm, AddTabdataDatasetForm, \
     ChangeTabdataDatasetCsvForm, EditTabdataDatasetForm, \
     AddCsvToDatasetForm, AddTabdataQueryForm
from tutorial.models import User, db, Dataset, Csv_fileref, \
     Query, Query_instance, Gps_remap
from tutorial.models import Tabdata_dataset, Tabdata_query, \
     Tabdata_query_instance
from marion_biblio.progressivegenerators import QueueReporter
from tutorial.geocache import get_location
import json
import logging
import gevent
tutorial_bp = Blueprint('tutorial_bp', __name__, template_folder='templates')


def authorlink_filter(s):
    return 'http://scholar.google.com/scholar?q={0}'.format(s)

tutorial_bp.add_app_template_filter(authorlink_filter, "authorlink")


@tutorial_bp.before_request
def before_request():
    g.user = current_user


@tutorial_bp.route("/logout")
def logout():
    logout_user()
    return redirect(url_for('index'))


# @oid.after_login
def after_login(resp):
    if resp.email is None or resp.email == "":
        flash('Invalid login.  Please try again.')
        return redirect(url_for('login'))
    user = User.query.filter_by(email=resp.email).first()
    if user is None:
        nickname = resp.nickname
        if nickname is None or nickname == "":
            nickname = resp.email.split("@")[0]
        user = User(nickname=nickname, email=resp.email)
        db.session.add(user)
        db.session.commit()
    remember_me = False
    if 'remember_me' in session:
        remember_me = session['remember_me']
        session.pop('remember_me', None)
    login_user(user, remember=remember_me)
    return redirect(request.args.get('next') or url_for('index'))

# @app.route("/upload")


@tutorial_bp.route("/")
@tutorial_bp.route("/index")
@login_required
def index():
    user = g.user
    return render_template('index.html',
                           title='Home',
                           user=user,
                           datasets=list(user.datasets),
                           tabdata_datasets=list(user.tabdata_datasets))

@tutorial_bp.route('/upload_file/', methods=("GET", "POST"))
@login_required
def upload_file():
    form = FileUploadForm()
    filename = None
    if form.validate_on_submit():
        current_user.add_file(form.file_1.data)
        return redirect(url_for('tutorial_bp.index'))
    else:
        filename = None
    # print("Errors: " + str(form.errors))
    return render_template('upload_file.html',
                           form=form, filename=filename)


@tutorial_bp.route('/add_dataset/', methods=('GET', 'POST'))
@login_required
def add_dataset():
    form = AddDatasetForm()
    if form.validate_on_submit():
        current_user.add_dataset(form.descriptionField.data,
                                 form.queryField.data)
        return redirect(url_for('tutorial_bp.index'))
    else:
        pass
    return render_template('add_dataset.html', form=form)


@tutorial_bp.route('/add_tabdata_dataset/', methods=('GET', 'POST'))
@login_required
def add_tabdata_dataset():
    """
    adds a tabular (CSV) dataset
    """
    form = AddTabdataDatasetForm()
    if form.validate_on_submit():
        new_set = current_user.add_tabdata_dataset(
            form.descriptionField.data, form.file_1.data)
        return redirect(
            url_for('tutorial_bp.edit_tabdata_dataset',
                    **{'tabdata_dataset_id': new_set.id}))
    else:
        flash("Error in form validation: " + repr(form.errors))
    return render_template('add_tabdata_dataset.html', form=form)


@tutorial_bp.route('/edit_tabdata_dataset/<tabdata_dataset_id>',
                   methods=('GET', 'POST'))
@login_required
def edit_tabdata_dataset(tabdata_dataset_id):
    """
    Edits an existing dataset, allowing change of description and CSV file
    """
    dataset = Tabdata_dataset.query.get(int(tabdata_dataset_id))
    upload_form = ChangeTabdataDatasetCsvForm()
    edit_form = EditTabdataDatasetForm()
    add_query_form = AddQueryToDatasetForm()
    add_query_form.query.choices = \
      [(q.id, q.name) for q in Tabdata_query.query.order_by('name')]
    if upload_form.validate_on_submit():
        dataset.add_csv(upload_form.file_1.data)
        flash("File updated")
        return redirect(url_for(
            'tutorial_bp.edit_tabdata_dataset',
            **{'tabdata_dataset_id': dataset.id}))
    else:
        if len(upload_form.errors) > 0:
            flash("Upload form error: " + repr(upload_form.errors))
    if edit_form.validate_on_submit():
        if edit_form.verifyDeleteCheckbox.data is True \
          and edit_form.delete_button.data is True:
            db.session.delete(dataset)
            db.session.commit()
            return redirect(url_for('tutorial_bp.index'))
    else:
        if len(edit_form.errors) > 0:
            flash("Edit form error: " + repr(edit_form.errors))
    if add_query_form.validate_on_submit():
        # dataset.add_query_instance(add_query_form.query.data)
        flash("Tabdata query added!")
        return redirect(
            url_for('tutorial_bp.add_tabdata_dataset_query',
                    **{'tabdata_dataset_id': dataset.id,
                        'tabdata_query_id': add_query_form.query.data}))
    else:
        if len(add_query_form.errors) > 0:
            flash("Add query form error: " + repr(add_query_form.errors))
    return render_template(
        'edit_tabdata_dataset.html',
        tabdata_dataset=dataset,
        upload_form=upload_form,
        add_query_form=add_query_form,
        edit_form=edit_form)


@tutorial_bp.route(
    '/add_tabdata_dataset_query/<tabdata_dataset_id>_add_<tabdata_query_id>',
    methods=("GET", "POST"))
@login_required
def add_tabdata_dataset_query(tabdata_dataset_id, tabdata_query_id):
    """
    """
    dataset = Tabdata_dataset.query.get(int(tabdata_dataset_id))
    query = Tabdata_query.query.get(int(tabdata_query_id))
    parameters = json.loads(query.parameters)

    form = AddTabdataQueryForm(
        parameterFields=[{'name': key, 'choices': dataset.column_choices()}
                         for key, value in parameters.items()])
    form.setParameterChoices(parameters, dataset.column_choices())

    if form.submitButton.data is True:
        instance_parameters = {}
        for i in range(len(form.parameterFields)):
            instance_parameters[form.parameterFields[i].id] \
              = form.parameterFields[i].data
        dataset.add_query_instance(tabdata_query_id,
                                   json.dumps(instance_parameters))
        return redirect(
            url_for('tutorial_bp.edit_tabdata_dataset',
                    **{'tabdata_dataset_id': dataset.id}))
    else:
        flash("Error: " + repr(form.errors))
    return render_template(
        'add_tabdata_dataset_query.html',
        tabdata_dataset=dataset,
        tabdata_query=query, form=form)


@tutorial_bp.route('/delete_tabfile/<tabfile_id>')
@login_required
def delete_tabfile(tabfile_id):
    tabfile = Csv_fileref.query.get(int(tabfile_id))
    dataset_id = tabfile.dataset.id
    # delete the actual file
    if os.path.exists(tabfile.stored_fullpath()):
        os.remove(tabfile.stored_fullpath())
    # now delete the fileref
    db.session.delete(tabfile)
    db.session.commit()
    return redirect(url_for(
        'tutorial_bp.edit_dataset',
        **{'dataset_id': dataset_id}))


@tutorial_bp.route(
    '/delete_tabdata_query_instance/<tabdata_query_instance_id>')
@login_required
def delete_tabdata_query_instance(tabdata_query_instance_id):
    query_instance = Tabdata_query_instance.query.get(
        int(tabdata_query_instance_id))
    dataset_id = query_instance.dataset.id
    db.session.delete(query_instance)
    db.session.commit()
    return redirect(url_for(
        'tutorial_bp.edit_tabdata_dataset',
        **{'tabdata_dataset_id': dataset_id}))


@tutorial_bp.route('/delete_query_instance/<query_instance_id>')
@login_required
def delete_query_instance(query_instance_id):
    query_instance = Query_instance.query.get(int(query_instance_id))
    dataset_id = query_instance.dataset.id
    if os.path.exists(query_instance.stored_fullpath()):
        os.remove(query_instance.stored_fullpath())
    db.session.delete(query_instance)
    db.session.commit()
    return redirect(url_for(
        'tutorial_bp.edit_dataset',
        **{'dataset_id': dataset_id}))


@tutorial_bp.route('/edit_dataset/<dataset_id>', methods=('GET', 'POST'))
@login_required
def edit_dataset(dataset_id):
    dataset = Dataset.query.get(int(dataset_id))
    upload_form = AddCsvToDatasetForm()
    add_query_form = AddQueryToDatasetForm()
    add_query_form.query.choices = [(q.id, q.name)
                                    for q in Query.query.order_by('name')]
    if upload_form.validate_on_submit():
        dataset.add_csv(upload_form.file_1.data)
        return redirect(url_for('tutorial_bp.edit_dataset',
                                **{'dataset_id': dataset.id}))
    if add_query_form.validate_on_submit():
        dataset.add_query_instance(add_query_form.query.data)
        return redirect(url_for('tutorial_bp.edit_dataset',
                                **{'dataset_id': dataset.id}))
    return render_template(
        'edit_dataset.html',
        dataset=dataset,
        upload_form=upload_form,
        add_query_form=add_query_form)


@tutorial_bp.route('/regenerate_h5/<dataset_id>', methods=('GET', 'POST'))
@login_required
def regenerate_h5(dataset_id):
    dataset = Dataset.query.get(int(dataset_id))
    dataset.regenerate_h5_file()
    return redirect(url_for('tutorial_bp.edit_dataset',
                            **{'dataset_id': dataset_id}))


# example of SSEs from flask.pocoo.org/snippets/116
class ServerSentEvent():

    def __init__(self, data):
        self.data = data
        self.event = None
        self.id = None
        self.desc_map = {
            self.data: "data",
            self.event: "event",
            self.id: "id"
        }

    def encode(self):
        if not self.data:
            return ""
        lines = ["%s: %s" % (v, k)
                 for k, v in self.desc_map.items() if k]

        return "%s\n\n" % "\n".join(lines)


@tutorial_bp.route('/regenerate_h5_progress/<dataset_id>',
                   methods=('GET', 'POST'))
@login_required
def regenerate_h5_progress(dataset_id):

    reporter = QueueReporter(length_hint=0)
    dataset = Dataset.query.get(int(dataset_id))
    reporter.length_hint = dataset.csv_rows()

    @copy_current_request_context
    def do_action():
        dataset.regenerate_h5_file(progress_reporter=reporter)
    g1 = gevent.spawn(do_action)

    @copy_current_request_context
    def reportGen():
        try:
            while True:
                progress = reporter.queue.get()
                print(progress)
                ev = ServerSentEvent(json.dumps(dict(step=progress[0],
                                                     length=progress[1])))
                yield ev.encode()
                gevent.sleep(0)
        except GeneratorExit:
            print("Gen exit!")
            yield ServerSentEvent("done").encode()

    gevent.joinall([
        g1,
        # gevent.spawn(report)
    ])
    # return redirect(url_for('tutorial_bp.edit_dataset', **{'dataset_id': dataset_id}))
    return Response(reportGen(), mimetype='text/event-stream')


@tutorial_bp.route('/view_query_instance/<query_instance_id>',
                   methods=('GET', 'POST'))
@login_required
def view_query_instance(query_instance_id):
    query_instance = Query_instance.query.get(int(query_instance_id))
    return render_template(query_instance.query_def.template,
                           query_data=query_instance.retrieve_data())


@tutorial_bp.route("/view_tabdata_query_instance/<tabdata_query_instance_id>",
                   methods=('GET', 'POST'))
@login_required
def view_tabdata_query_instance(tabdata_query_instance_id):
    """

    Arguments:
    - `tabdata_query_instance_id`:
    """
    query_instance = Tabdata_query_instance.query.get(
        int(tabdata_query_instance_id))
    return render_template(query_instance.query_def.template,
                           query_data=query_instance.retrieve_data())


@tutorial_bp.route('/vis_tabdata_query_instance/<tabdata_query_instance_id>',
                   methods=('GET', 'POST'))
@login_required
def vis_tabdata_query_instance(tabdata_query_instance_id):
    query_instance = Tabdata_query_instance.query.get(
        int(tabdata_query_instance_id))
    data = query_instance.retrieve_data()
    return render_template("vis_" + query_instance.query_def.template,
                           tabdata_query_instance_id=tabdata_query_instance_id,
                           tabdata_query_instance=query_instance,
                           query_data=data)


@tutorial_bp.route('/vis_query_instance/<query_instance_id>',
                   methods=('GET', 'POST'))
@login_required
def vis_query_instance(query_instance_id):
    query_instance = Query_instance.query.get(int(query_instance_id))
    return render_template("vis_"+query_instance.query_def.template,
                           query_instance_id=query_instance_id,
                           query_instance=query_instance,
                           query_data=query_instance.retrieve_data())


@tutorial_bp.route('/make_gps_remap/<remap_loc>', methods=('GET', 'POST'))
@login_required
def make_gps_remap(remap_loc):
    """

    Arguments:
    - `remap_loc`: string to remap
    """
    last_lookup_lat = request.args.get('last_lookup_lat')
    last_lookup_lon = request.args.get('last_lookup_lon')
    last_remap = request.args.get('last_remap')
    remap_form = MakeGpsRemapForm()
    if remap_form.remap_to.data is None:
        remap_form.remap_to.data = last_remap
    remap_form.remap_to.label = "Remap To:"
    if remap_form.validate_on_submit():
        # multiple buttons; read value based on name, and switch on value
        if remap_form.test_button.data is True:
            last_remap = remap_form.remap_to.data
            last_lookup = get_location(last_remap, False)
            last_lookup_lat = last_lookup['lat'] if last_lookup is not None \
              else None
            last_lookup_lon = last_lookup['lon'] if last_lookup is not None \
              else None
        elif remap_form.remap_button.data is True:
            last_remap = remap_form.remap_to.data
            remap = Gps_remap.query.get(remap_loc)
            logging.warning(remap)
            if remap is None:
                remap = Gps_remap(from_location=remap_loc,
                                  to_location=last_remap)
                db.session.add(remap)
            remap.to_location = last_remap
            db.session.commit()
            flash("Remap for {0} added; you can close this window".format(
                last_remap))
        return redirect(url_for('tutorial_bp.make_gps_remap',
                                ** {'remap_loc': remap_loc,
                                    'last_remap': last_remap,
                                    'last_lookup_lat': last_lookup_lat,
                                    'last_lookup_lon': last_lookup_lon
                                    }))
    return render_template("make_gps_remap.html",
                           remap_loc=remap_loc,
                           last_lookup_lat=last_lookup_lat,
                           last_lookup_lon=last_lookup_lon,
                           last_remap=last_remap,
                           remap_form=remap_form)
