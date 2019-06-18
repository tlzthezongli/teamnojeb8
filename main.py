import webapp2
import jinja2
import os
from google.appengine.api import users
from google.appengine.api import urlfetch
import json
from google.appengine.ext import ndb
from models import Manga, MangaUser
import random

JINJA_ENVIRONMENT = jinja2.Environment(
    loader=jinja2.FileSystemLoader(os.path.dirname(__file__)),
    extensions=['jinja2.ext.autoescape'],
    autoescape=True)

#mainpage just to redirect users
class MainPageHandler(webapp2.RequestHandler):
  def get(self):
    user = users.get_current_user()
    # If the user is logged in...
    if user:
      email_address = user.nickname()
      manga_user = MangaUser.query().filter(MangaUser.email == email_address).get()
      # If the user is registered...
      if manga_user:
        self.redirect('/homepage')
      # If the user isn't registered...
      else:
        # Offer a registration form for a first-time visitor:
        self.response.write('''
            Welcome to our site, %s!  Please sign up! <br>
            <form method="post" action="/">
            <input type="text" name="username" placeholder='Enter a username...'>
            <input type="submit">
            </form>
            ''' % (email_address))
    else:
      # If the user isn't logged in...
      self.redirect('/login')

  def post(self):
    # Code to handle a first-time registration from the form:
    user = users.get_current_user()
    name=self.request.get('username')
    manga_user = MangaUser(
        username=self.request.get('username'),
        email=user.nickname(),
        user_ratings={},
        user_reviews={},
        friends_list={})
    manga_user.put()
    self.response.write('Thanks for signing up, %s! <br>Go to the <a href="/homepage">Home</a> page' %
        manga_user.username)

class NoUserHandler(webapp2.RequestHandler):
    def get(self):
        login_url = users.create_login_url("/")
        self.response.write('Please log in. <a href="' + login_url + '">Click here to login</a>')

#user is loggedin
class LoggedInHandler(webapp2.RequestHandler):
    def get(self):
        user = users.get_current_user()
        if user:
            manga_user = MangaUser.query().filter(MangaUser.email == user.nickname()).get()
            # If the user is registered...
            if manga_user:
                hometemplate = JINJA_ENVIRONMENT.get_template('templates/homepage.html')
                logout_url = users.create_logout_url("/")
                d = {'logout': logout_url}
                manga_user = MangaUser.query().filter(MangaUser.email == user.nickname()).get()
                # print(manga_user)
                mangausers = MangaUser.query().filter(MangaUser.email != user.nickname()).fetch()
                print(mangausers)

                e={}
                f={}
                for i in range(len(mangausers)):
                    if mangausers[i].username not in manga_user.friends_list:
                        e[i]={'key':mangausers[i].key,
                              'username': mangausers[i].username,
                              'rating':mangausers[i].user_ratings,
                              'reviews':mangausers[i].user_reviews}
                    else:
                        f[i]={'key':mangausers[i].key,
                              'username': mangausers[i].username,
                              'rating':mangausers[i].user_ratings,
                              'reviews':mangausers[i].user_reviews}
                if len(e)-5>0:
                    list = generaterandom(len(e))
                    for i in range(len(list)):
                        del e[list[i]]
                d['e']=e
                d['f']=f
                # print(d['e'][0]['key'].id())

                self.response.write("Hello " + manga_user.username + '. You are logged in.')
                self.response.write(hometemplate.render(d))
            else:
                self.response.write('Pls sign up for our page')
        else:
            self.response.write("Sorry, this page is only for logged in users.")

class SearchBarHandler(webapp2.RequestHandler):
    def post(self):
        searchtemplate = JINJA_ENVIRONMENT.get_template('templates/tryanime1.html')
        searchTerm=self.request.get('search')
        searchTerm=searchTerm.replace(' ','%20')
        endpoint_url='https://kitsu.io/api/edge/manga?page[limit]=20&filter[text]='+searchTerm
        response = urlfetch.fetch(endpoint_url)
        content = response.content
        response_as_json = json.loads(content)
        d={}
        if response_as_json['data']==[]:
            error='No manga found. Check your spelling'
        else:
            error=''
            for i in range(len(response_as_json['data'])):
                image_url=response_as_json['data'][i]['attributes']['posterImage']['medium']
                titles=response_as_json['data'][i]['attributes']['canonicalTitle']
                mangaid=response_as_json['data'][i]['id']
                d[i]=[image_url,titles,mangaid]
        #print(d)
        dd = {'d': d, 'e':error}
        self.response.write(searchtemplate.render(dd))

class MangaHandler(webapp2.RequestHandler):
    def get(self, name):
        mangatemplate = JINJA_ENVIRONMENT.get_template('templates/manga.html')
        # print (name)
        text=''
        user = users.get_current_user()
        manga_user=MangaUser.query().filter(MangaUser.email == user.nickname()).get()

        if name in manga_user.user_ratings:
            text = 'You have already rated this manga. Do you want to rate this again?'
        else:
            text = 'Rate this manga'
        endpoint_url='https://kitsu.io/api/edge/manga/'+name
        # print(endpoint_url)
        response = urlfetch.fetch(endpoint_url)
        #print(response.status_code)
        content = response.content
        # print(content)
        response_as_json = json.loads(content)
        # print(response_as_json)
        d={}
        image_url=response_as_json['data']['attributes']['posterImage']['medium']
        titles=response_as_json['data']['attributes']['canonicalTitle']
        synopsis=response_as_json['data']['attributes']['synopsis']
        mangaid=response_as_json['data']['id']
        d['info']=[image_url,titles,synopsis,mangaid,text]
        # print(d)
        # print(manga_user)
        self.response.write(mangatemplate.render(d))
        manga = Manga(
            manga_id=d['info'][3],
            manga_title = d['info'][1],
            reviews={},
            total_ratings={},
        )
        manga.put()
    def post( self,name):
        # print(name)
        mangatemplate = JINJA_ENVIRONMENT.get_template('templates/manga.html')
        user = users.get_current_user()
        manga_user=MangaUser.query().filter(MangaUser.email == user.nickname()).get()
        # print(manga_user.user_ratings)
        rating = self.request.get("rating")
        review = self.request.get('review')
        endpoint_url='https://kitsu.io/api/edge/manga/'+name

        # print(endpoint_url)
        response = urlfetch.fetch(endpoint_url)
        #print(response.status_code)
        content = response.content
        # print(content)
        response_as_json = json.loads(content)
        # print(response_as_json)
        d={}
        image_url=response_as_json['data']['attributes']['posterImage']['medium']
        titles=response_as_json['data']['attributes']['canonicalTitle']
        synopsis=response_as_json['data']['attributes']['synopsis']
        mangaid=response_as_json['data']['id']
        text = 'You have already rated this manga. Do you want to rate this again?'
        d['info']=[image_url,titles,synopsis,mangaid,text]
        # print(rating)
        if rating =='' and review =='':
            pass
        elif review =='':
            manga_user.user_ratings[name]=float(rating)
        else:
            manga_user.user_ratings[name]=float(rating)
            manga_user.user_reviews[name]=review
        # print(manga_user.user_ratings)
        manga_user.put()
        manga = Manga.query().filter(Manga.manga_title == d['info'][3]).fetch()
        print (manga)
        #manga.manga_id = name
        #manga.reviews.append(review)
        #manga.ratings.append(rating)
        #anga.put()
        for review in len(manga.reviews):
            pass
        self.response.write(mangatemplate.render(d))

class FriendHandler(webapp2.RequestHandler):
    def get(self,name):
        friendtemplate = JINJA_ENVIRONMENT.get_template('templates/friend.html')
        user = users.get_current_user()
        manga_user=MangaUser.query().filter(MangaUser.email == user.nickname()).get()
        logout_url = users.create_logout_url("/")
        mangauser=MangaUser.query().fetch()
        text=''
        d={}
        name1 = int(name)
        for i in range(len(mangauser)):
            if mangauser[i].key.id() == name1:
                d={'username': mangauser[i].username, 'id':name1}
        if d['username'] not in manga_user.friends_list:
            text = "Click to follow user"
        else:
            text='Following. Click to Unfollow'
        d['text']=text
        d['logout']=logout_url
        self.response.write(friendtemplate.render(d))
    def post(self,name):
        friendtemplate = JINJA_ENVIRONMENT.get_template('templates/friend.html')
        user = users.get_current_user()
        manga_user=MangaUser.query().filter(MangaUser.email == user.nickname()).get()
        logout_url = users.create_logout_url("/")
        mangauser=MangaUser.query().fetch()
        text=''
        d={}
        name1 = int(name)
        for i in range(len(mangauser)):
            if mangauser[i].key.id() == name1:
                d={'username': mangauser[i].username, 'id':name1, 'friend':mangauser[i]}
        if d['username'] not in manga_user.friends_list:
            manga_user.followfriend(d['friend'])
            text='Following. Click to unfollow'
        else:
            manga_user.removefriend(d['friend'])
            text='Click to follow user'
        manga_user.put()
        print(manga_user)
        d['text']=text
        d['logout']=logout_url
        self.response.write(friendtemplate.render(d))

def CalculateRating(manga_id,rating):
    Manga.total_ratings.append(rating)
    sum = 0
    for n in manga.total_ratings:
        sum += n
    Manga.average_ratings = sum
    Manga.put()

def generaterandom(length):
    listofrandom=[]
    while len(listofrandom)!=length-5:
        no= random.randint(0,length-1)
        if no not in listofrandom:
            listofrandom.append(no)
    return (listofrandom)



app = webapp2.WSGIApplication([
    ('/', MainPageHandler),
    ('/login', NoUserHandler),
    ('/homepage', LoggedInHandler),
    ('/search', SearchBarHandler),
    ('/manga/(\w+)', MangaHandler),
    ('/friend/(\w+)', FriendHandler),
], debug=True)
