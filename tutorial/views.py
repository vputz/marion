import os
from flask import render_template, flash, redirect, session, url_for, request, g, current_app, request
from flask.ext.login import login_user, logout_user, login_required
from flask.ext.security import current_user
#, oid
from tutorial.forms import LoginForm, FileUploadForm, AddDatasetForm, AddCsvToDatasetForm
from tutorial.models import User, db, Dataset, Csv_fileref
from werkzeug import secure_filename
from flask import Blueprint
#, ROLE_USER, ROLE_ADMIN

tutorial_bp = Blueprint('tutorial_bp', __name__, template_folder= 'templates' )

@tutorial_bp.before_request
def before_request() :
    g.user = current_user

#@lm.user_loader
#def load_user(id) :
#    return User.query.get(int(id))

#@app.route('/login', methods=['GET', 'POST'])
#@oid.loginhandler
#def login() :
#    if g.user is not None and g.user.is_authenticated() :
#        return redirect( url_for('index') )
#    form = LoginForm()
#    if form.validate_on_submit() :
#        session['remember_me'] = form.remember_me.data
#        return oid.try_login( form.openid.data, ask_for=['nickname','email'])
#    return render_template('login.html', title='Sign In', form=form, providers=app.config['OPENID_PROVIDERS'] )

@tutorial_bp.route("/logout")
def logout() :
    logout_user()
    return redirect(url_for('index'))

#@oid.after_login
def after_login(resp) :
    if resp.email is None or resp.email == "" :
        flash('Invalid login.  Please try again.')
        return redirect(url_for('login'))
    user = User.query.filter_by(email = resp.email).first()
    if user is None :
        nickname = resp.nickname
        if nickname is None or nickname == "" :
            nickname = resp.email.split("@")[0]
        user = User( nickname=nickname, email=resp.email )
        db.session.add( user )
        db.session.commit()
    remember_me= False
    if 'remember_me' in session:
        remember_me = session['remember_me']
        session.pop('remember_me', None)
    login_user( user, remember = remember_me )
    return redirect(request.args.get('next') or url_for('index'))

#@app.route("/upload")


@tutorial_bp.route("/")
@tutorial_bp.route("/index")
@login_required
def index() :
    user = g.user
    return render_template('index.html',
                           title='Home',
                           user=user, datasets= list(user.datasets) )

@tutorial_bp.route('/upload_file/', methods=("GET","POST") )
@login_required
def upload_file() :
    form = FileUploadForm()
    filename = None
    if form.validate_on_submit() :
        current_user.add_file( form.file_1.data )
        return redirect(url_for('tutorial_bp.index'))
    else :
        filename = None
    #print( "Errors: " + str( form.errors ))
    return render_template( 'upload_file.html', form=form, filename=filename )

@tutorial_bp.route('/add_dataset/', methods=('GET','POST') )
@login_required
def add_dataset() :
    form = AddDatasetForm()
    if form.validate_on_submit() :
        current_user.add_dataset( form.descriptionField.data, form.queryField.data )
        return redirect(url_for('tutorial_bp.index'))
    else :
        pass
    return render_template('add_dataset.html', form=form )

@tutorial_bp.route('/delete_tabfile/<tabfile_id>')
@login_required
def delete_tabfile( tabfile_id ) :
    tabfile = Csv_fileref.query.get( int(tabfile_id) )
    dataset_id = tabfile.dataset.id
    # delete the actual file
    os.remove( tabfile.stored_fullpath() )
    # now delete the fileref
    db.session.delete( tabfile )
    db.session.commit()
    return redirect( url_for('tutorial_bp.edit_dataset', **{ 'dataset_id' : dataset_id } ) )

@tutorial_bp.route('/edit_dataset/<dataset_id>', methods=('GET','POST') )
@login_required
def edit_dataset( dataset_id ) :
    dataset = Dataset.query.get(int(dataset_id))
    upload_form = AddCsvToDatasetForm()
    if upload_form.validate_on_submit() :
        dataset.add_csv( upload_form.file_1.data )
        return redirect( url_for( 'tutorial_bp.edit_dataset', **{ 'dataset_id' : dataset.id } ) )
    return render_template('edit_dataset.html', dataset = dataset, upload_form = upload_form )

@tutorial_bp.route('/regenerate_h5/<dataset_id>', methods=('GET', 'POST') )
@login_required
def regenerate_h5( dataset_id ) :
    dataset = Dataset.query.get( int(dataset_id))
    dataset.regenerate_h5_file()
    return redirect( url_for('tutorial_bp.edit_dataset', **{ 'dataset_id' : dataset_id } ) )
    
