from flask.ext.restful import Api, Resource, reqparse
import werkzeug
from flask.ext.security import current_user 
import os.path

from tutorial import models

api = Api()

class UserAPI( Resource ) :
    def get(self, id):
        u = models.User.query.get(id)
        return { 'nickname' : u.nickname, 'id' : u.id, 'email': u.email }

    def put(self,id) :
        pass

    def delete(self, id) :
        pass

api.add_resource(UserAPI, '/users/<int:id>', endpoint = 'user' )

class TaskListAPI( Resource) :
    def __init__(self) :
        self.reqparse = reqparse.RequestParser()
        self.reqparse.add_argument('title', type= str, required= True,
                                   help='No task title provided', location='json')
        self.reqparse.add_argument('description', type=str, default='', location='json')
        super( TaskListAPI, self).__init__()
    
    def get(self ) :
        pass

    def post(self) :
        pass

class TaskAPI( Resource ) :
    def get( self, id ) :
        pass

    def put( self, id ) :
        pass

    def delete(self, id ) :
        pass

api.add_resource( TaskListAPI, '/todo/api/v1.0/tasks', endpoint = 'tasks' )
api.add_resource( TaskAPI, '/todo/api/v1.0/tasks/<int:id>', endpoint = 'task' )

class UploadAPI( Resource ) :

    def __init__( self ) :
        self.reqparse = reqparse.RequestParser()
        self.reqparse.add_argument('files', type=werkzeug.datastructures.FileStorage, location='files', required=True, help='File to upload' )
        super( UploadAPI, self).__init__()
        pass

    def post( self ) :
        #print( request.files )
        args = self.reqparse.parse_args()
        #print("Args: " + str(args))
        file = args['files']
        current_user.add_file( file )
                  

api.add_resource( UploadAPI, '/upload', endpoint = 'upload' )
