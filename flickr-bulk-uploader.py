import os
import simplejson
import flickrapi

api_secret = 'a131ba6ac653b986'
api_key = 'dced4d69f72c55375dd72f12d2a3941b'

PHOTOS_DIRECTORY = '/home/humitos/fotos'


class Flickr(object):

    def __init__(self, api_key, api_secret, format='etree'):
        self.api_key = api_key
        self.api_secret = api_secret
        self.format = format
        self.api = flickrapi.FlickrAPI(api_key, api_secret, format=self.format)
        (token, frob) = self.api.get_token_part_one(perms='write')
        self.token = self.api.get_token_part_two((token, frob))
        self.cache = {'photoset_photos': {}}

    def get_photoset_list(self):
        if 'photoset_list' in self.cache.keys():
            return self.cache['photoset_list']
        else:
            photoset_list = self.api.photosets_getList(format=self.format)
            if self.format == 'json':
                r = simplejson.loads(photoset_list[14:-1])
            else:
                r = photoset_list
            self.cache['photoset_list'] = r
            return r

    def is_photoset_already_created(self, photoset_name):
        for ps in self.get_photoset_list()['photosets']['photoset']:
            if ps['title']['_content'] == photoset_name:
                return (True, ps['id'])
        return (False, 0)

    def is_photo_already_uploaded(self, photo_name, photoset_name):
        for ps in self.get_photoset_list()['photosets']['photoset']:
            if ps['title']['_content'] == photoset_name:
                for photo in self.get_photoset_photos(ps['id'])['photoset']['photo']:
                    if photo['title'] == photo_name[:-4]:
                        return True
                return False
        return False

    def get_photoset_photos(self, photoset_id):
        if 'photoset_photos' in self.cache.keys() and \
           photoset_id in self.cache['photoset_photos'].keys():
            return self.cache['photoset_photos'][photoset_id]
        else:
            photoset_photos = self.api.photosets_getPhotos(
                photoset_id=photoset_id)
            if self.format == 'json':
                r = simplejson.loads(photoset_photos[14:-1])
            else:
                r = photoset_photos
            self.cache['photoset_photos'][photoset_id] = r
            return r

    def create_photoset(self, photoset_name, primary_photo_id):
        photoset = self.api.photosets_create(title=photoset_name,
                                             primary_photo_id=primary_photo_id)
        if self.format == 'json':
            return simplejson.loads(photoset[14:-1])
        else:
            return photoset

    def add_photo_to_photoset(self, photoset_id, photo_id):
        self.api.photosets_addPhoto(photoset_id=photoset_id,
                                    photo_id=photo_id)

    def upload_all_photos(self, directory):
        for root, dirs, files in os.walk(directory):
            if dirs != []:
                continue
            else:
                print 'Subiendo fotos de:'
                print '    %s' % root
                photoset_title = os.path.basename(root)

                for filename in files:
                    path = os.path.join(root, filename)
                    print '      - %s' % path

                    if not self.is_photo_already_uploaded(filename,
                                                          photoset_title):
                        upload = self.upload_photo(path, 0)
                        if upload.get('stat') == 'ok':
                            created, photoset_id = self.is_photoset_already_created(photoset_title)
                            photo_id = upload.find('photoid').text
                            if created:
                                self.add_photo_to_photoset(photoset_id, photo_id)
                            else:
                                self.create_photoset(photoset_title, photo_id)
                    else:
                        print 'Esta foto ya fue subida a Flickr: %s' % filename

    def upload_photo(self, path, is_public):
        upload = self.api.upload(filename=path,
                                 is_public=is_public, format='etree')
        return upload


if __name__ == '__main__':
    api = Flickr(api_key, api_secret, format='json')
    api.upload_all_photos(PHOTOS_DIRECTORY)
