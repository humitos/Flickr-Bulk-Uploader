import os
import json
import flickrapi
import webbrowser
import pdb

from settings import PHOTOS_DIRECTORY, api_key, api_secret, EXCLUDE_FILES_REGEX


class Flickr(object):

    def __init__(self, api_key, api_secret, format='etree'):
        self.api_key = api_key
        self.api_secret = api_secret
        self.format = format
        self.api = flickrapi.FlickrAPI(api_key, api_secret, format=self.format)

        print('Step 1: Authenticate')

        # Only do this if we don't have a valid token already
        if not self.api.token_valid(perms='write'):

            # Get a request token
            self.api.get_request_token(oauth_callback='oob')

            # Open a browser at the authentication URL. Do this however
            # you want, as long as the user visits that URL.
            authorize_url = self.api.auth_url(perms='write')
            webbrowser.open_new_tab(authorize_url)

            # Get the verifier code from the user. Do this however you
            # want, as long as the user gives the application the code.
            verifier = str(input('Verifier code: '))

            # Trade the request token for an access token
            self.api.get_access_token(verifier)

        print('Step 2: Use Flickr')

        self.cache = {'photoset_photos': {}}

    def get_photoset_list(self, force=False):
        if 'photoset_list' in self.cache.keys() and not force:
            return self.cache['photoset_list']
        else:
            photoset_list = self.api.photosets_getList(format=self.format)
            if self.format == 'json':
                r = json.loads(photoset_list.decode('utf-8'))
            else:
                r = photoset_list
            self.cache['photoset_list'] = r
            return r

    def is_photoset_already_created(self, photoset_name):
        for ps in self.get_photoset_list(force=False)['photosets']['photoset']:
            if ps['title']['_content'] == photoset_name:
                return (True, ps['id'])
        return (False, 0)

    def is_photo_already_uploaded(self, photo_name, photoset_name):
        for ps in self.get_photoset_list(force=False)['photosets']['photoset']:
            if ps['title']['_content'] == photoset_name:
                for photo in self.get_photoset_photos(ps['id'],
                                force=False)['photoset']['photo']:
                    if photo['title'] == photo_name[:-4]:
                        return True
                return False
        return False

    def get_photoset_photos(self, photoset_id, force=False):
        if 'photoset_photos' in self.cache.keys() and \
           photoset_id in self.cache['photoset_photos'].keys() and not force:
            return self.cache['photoset_photos'][photoset_id]
        else:
            photoset_photos = self.api.photosets_getPhotos(
                photoset_id=photoset_id)
            if self.format == 'json':
                r = json.loads(photoset_photos.decode('utf-8'))
            else:
                r = photoset_photos
            self.cache['photoset_photos'][photoset_id] = r
            return r

    def create_photoset(self, photoset_name, primary_photo_id):
        photoset = self.api.photosets_create(title=photoset_name,
                                             primary_photo_id=primary_photo_id)

        # update photoset_list cache
        self.get_photoset_list(force=True)

        if self.format == 'json':
            return json.loads(photoset.decode('utf-8'))
        else:
            return photoset

    def add_photo_to_photoset(self, photoset_id, photo_id):
        self.api.photosets_addPhoto(photoset_id=photoset_id,
                                    photo_id=photo_id)

        # update photoset_photos list cache
        self.get_photoset_photos(photoset_id, force=True)

    def upload_all_photos(self, directory):

        # Gets the name of the folders in the main 
        set_name_list = next(os.walk(directory))[1]
        for photoset_title in set_name_list:
            for root, dirs, files in os.walk(directory + '\\' + photoset_title):
                if dirs != []:
                    continue
                else:
                    print('Uploading the photos:')
                    print(root)
                    print('The SetName: ' + photoset_title)

                    for filename in files:
                        path = os.path.join(root, filename)
                        print(path)
                        if EXCLUDE_FILES_REGEX.match(path):
                            print('EXCLUDED')
                            continue

                        if not self.is_photo_already_uploaded(filename,
                                                              photoset_title):
                            try:
                                upload = self.upload_photo(path, 0)
                            except flickrapi.exceptions.FlickrError as e:
                                print(e)
                                import ipdb;ipdb.set_trace()
                                continue
                            if upload.get('stat') == 'ok':
                                created, photoset_id = self.is_photoset_already_created(photoset_title)
                                photo_id = upload.find('photoid').text
                                if created:
                                    self.add_photo_to_photoset(photoset_id, photo_id)
                                else:
                                    self.create_photoset(photoset_title, photo_id)
                        else:
                            print('The photo: ' + filename + 'is uploaded to Flickr')

    def upload_photo(self, path, is_public):
        upload = self.api.upload(filename=path,
                                 is_public=is_public, format='etree')
        return upload


if __name__ == '__main__':
    api = Flickr(api_key, api_secret, format='json')
    api.upload_all_photos(PHOTOS_DIRECTORY)
