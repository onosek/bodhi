import unittest
import json
import tw2.core as twc

from kitchen.iterutils import iterate
from nose.tools import eq_

app = None


def setup():
    from bodhi import main
    from webtest import TestApp
    global app
    app = main({}, testing=True, **{'sqlalchemy.url': 'sqlite://',
                      'mako.directories': 'bodhi:templates'})
    app = TestApp(twc.make_middleware(app))


class FunctionalTests(unittest.TestCase):

    def get_update(self, builds=None, stablekarma=3, unstablekarma=-3):
        if not builds:
            builds = 'bodhi-2.0-1'
        data = {
            'newupdateform:bugs:bugs': u'',
            'newupdateform:notes': u'this is a test update',
            'newupdateform:type_': u'bugfix',
            'newupdateform:karma:stablekarma': stablekarma,
            'newupdateform:karma:unstablekarma': unstablekarma,
            'newupdateform:id': u'',
            }
        for i, build in enumerate(iterate(builds)):
            data['newupdateform:packages:%d:package' % i] = build
        return data

    def test_release_view_json(self):
        res = app.get('/releases/F17', status=200)
        data = json.loads(res.body)
        eq_(data['context']['name'], 'F17')

    def test_invalid_release(self):
        app.get('/releases/F16', status=404)

    def test_releases_view_json(self):
        res = app.get('/releases', status=200)
        data = json.loads(res.body)
        eq_(data[u'entries'][0][u'name'], 'F17')

    def test_releases_view_invalid_bug(self):
        app.get('/bugs/abc', status=404)

    def test_releases_view_bug(self):
        res = app.get('/bugs/12345', status=200)
        data = json.loads(res.body)
        eq_(data[u'context'][u'bug_id'], 12345)

    def test_invalid_build_name(self):
        res = app.post('/save', self.get_update('invalidbuild-1.0'))
        assert 'Invalid build' in res, res

    def test_valid_tag(self):
        res = app.post('/save', self.get_update())
        assert 'Invalid tag' not in res, res

    def test_invalid_tag(self):
        res = app.post('/save', self.get_update('bodhi-1.0-1'))
        assert 'Invalid tag' in res, res

    def test_old_build(self):
        res = app.post('/save', self.get_update('bodhi-1.9-1'))
        assert 'Invalid build: bodhi-1.9-1 is older than bodhi-2.0-1' in res, res

    def test_duplicate_build(self):
        res = app.post('/save', self.get_update(['bodhi-2.0-2', 'bodhi-2.0-2']))
        assert 'Duplicate builds' in res, res

    def test_multiple_builds_of_same_package(self):
        res = app.post('/save', self.get_update(['bodhi-2.0-2', 'bodhi-2.0-3']))
        assert 'Multiple bodhi builds specified' in res, res

    def test_invalid_autokarma(self):
        res = app.post('/save', self.get_update(stablekarma=-1))
        assert 'Must be at least 1' in res, res
        res = app.post('/save', self.get_update(unstablekarma=1))
        assert 'Cannot be more than -1' in res, res

    def test_duplicate_update(self):
        res = app.post('/save', self.get_update('bodhi-2.0-1'))
        assert 'Update for bodhi-2.0-1 already exists' in res, res
