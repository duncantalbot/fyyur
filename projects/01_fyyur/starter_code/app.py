#----------------------------------------------------------------------------#
# Imports
#----------------------------------------------------------------------------#

import json
import dateutil.parser
import babel
from flask import Flask, render_template, request, Response, flash, redirect, url_for, abort
from flask_moment import Moment
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
import logging
from logging import Formatter, FileHandler
from flask_wtf import Form
from forms import *
import sys

#----------------------------------------------------------------------------#
# App Config.
#----------------------------------------------------------------------------#

app = Flask(__name__)
moment = Moment(app)
app.config.from_object('config')
db = SQLAlchemy(app)

migrate = Migrate(app, db)
#----------------------------------------------------------------------------#
# Models.
#----------------------------------------------------------------------------#

from models import *

#----------------------------------------------------------------------------#
# Filters.
#----------------------------------------------------------------------------#

def format_datetime(value, format='medium'):
  date = dateutil.parser.parse(value)
  if format == 'full':
      format="EEEE MMMM, d, y 'at' h:mma"
  elif format == 'medium':
      format="EE MM, dd, y h:mma"
  return babel.dates.format_datetime(date, format)

app.jinja_env.filters['datetime'] = format_datetime

#----------------------------------------------------------------------------#
# Controllers.
#----------------------------------------------------------------------------#

@app.route('/')
def index():
  return render_template('pages/home.html')

#  Venues
#  ----------------------------------------------------------------

@app.route('/venues')
def venues():
  data = []
  current_time = datetime.now().strftime('%Y-%m-%d %H:%S:%M')
  locations = Venue.query.group_by(Venue.id, Venue.state, Venue.city).all()

  for location in locations:
    location_venues = Venue.query.filter_by(city=location.city).filter_by(state=location.state).all()   

    venue_data = []    
    for venue in location_venues:
      print('City Venue', venue)
      upcoming_shows_count = len(db.session.query(Show).filter(Show.venue_id==venue.id).filter(Show.start_time > current_time).all())
      venue_data.append({
        'id': venue.id, 
        'name': venue.name, 
        'num_upcoming_shows': upcoming_shows_count,
      })
    if not any(val['city'] == location.city for val in data):
      data.append({ 
        'city': location.city, 
        'state': location.state, 
        'venues': venue_data,
      })
  return render_template('pages/venues.html', areas=data );


@app.route('/venues/search', methods=['POST'])
def search_venues():
  data = []
  search_input = request.form.get('search_term', '')
  results_found = db.session.query(Venue).filter(Venue.name.ilike(f'%{search_input}%')).all()  
  
  for result in results_found:
    upcoming_shows_count = len(db.session.query(Show).filter(Show.venue_id==result.id).filter(Show.start_time>datetime.now()).all())
    data.append({
      'id': result.id,
      'name': result.name,
      'num_upcoming_shows': upcoming_shows_count,
    })

  response={
    'count': len(results_found),
    'data': data,
  }
  return render_template('pages/search_venues.html', results=response, search_term=request.form.get('search_term', ''))


@app.route('/venues/<int:venue_id>')
def show_venue(venue_id):

  venue = Venue.query.get(venue_id)

  if venue:
    upcoming_shows = []
    past_shows = []
    current_time = datetime.now().strftime('%Y-%m-%d %H:%S:%M')
    result_upcoming_shows = db.session.query(Show).join(Artist).filter(Show.start_time > current_time).filter(Show.venue_id==venue.id).all()
    
    for show in result_upcoming_shows:
      upcoming_shows.append({
        'artist_id': show.artist.id,
        'artist_name': show.artist.name,
        'artist_image_link': show.artist.image_link,
        'start_time': show.start_time.strftime('%Y-%m-%d %H:%M:%S'),
      })  
    upcoming_shows_count = len(upcoming_shows)

    result_past_shows = db.session.query(Show).join(Artist).filter(Show.start_time < current_time).filter(Show.venue_id==venue.id).all()
    
    for show in result_past_shows:
      past_shows.append({
        'artist_id': show.artist.id,
        'artist_name': show.artist.name,
        'artist_image_link': show.artist.image_link,
        'start_time': show.start_time.strftime('%Y-%m-%d %H:%M:%S'),
      })
    past_shows_count = len(past_shows)

    data = {
      'id': venue.id,
      'name': venue.name,
      'genres': venue.genres,
      'address': venue.address,
      'city': venue.city,
      'state': venue.state,
      'phone': venue.phone,
      'website': venue.website,
      'facebook_link': venue.facebook_link,
      'seeking_talent': venue.seeking_talent,
      'seeking_description': venue.seeking_description,
      'image_link': venue.image_link,
      'past_shows"': past_shows,   
      'upcoming_shows': upcoming_shows,
      'past_shows_count': past_shows_count,
      'upcoming_shows_count': upcoming_shows_count,
    }
    return render_template('pages/show_venue.html', venue=data)

  return render_tamplate('errors/404.html')


#  Create Venue
#  ----------------------------------------------------------------

@app.route('/venues/create', methods=['GET'])
def create_venue_form():
  form = VenueForm()
  return render_template('forms/new_venue.html', form=form)

@app.route('/venues/create', methods=['POST'])
def create_venue_submission():

  error = False
  try:   
    print('CREATE')
    name = request.form['name']
    city = request.form['city']
    state = request.form['state']
    address = request.form['address']
    phone = request.form['phone']
    genres = request.form.getlist('genres')
    image_link = request.form['image_link']
    facebook_link = request.form['facebook_link']
    website = request.form['website']
    seeking_talent = True if 'seeking_talent' in request.form else False
    seeking_description = request.form['seeking_description']

    venue = Venue(
      name=name, 
      city=city, 
      state=state, 
      address=address, 
      phone=phone, 
      genres=genres, 
      image_link=image_link,
      facebook_link=facebook_link,
      website=website,
      seeking_talent=seeking_talent,
      seeking_description=seeking_description,
    )
    print(venue)
    db.session.add(venue)
    print(venue)
    db.session.commit()
  except:
    error = True
    db.session.rollback()
    print(sys.exc_info())
  finally:
    db.session.close()

  if not error:
    flash('Venue ' + request.form['name'] + ' was successfully listed!')
  if error:
    flash('An error occurred. Venue ' + request.form['name'] + ' could not be listed!')
  
  return render_template('pages/home.html')


@app.route('/venues/<venue_id>', methods=['DELETE'])
def delete_venue(venue_id):
 
  error = False
  try:
    venue = Venue.query.get(venue_id)
    db.session.delete(venue)
    db.session.commit()
  except:
    error = True
    db.session.rollback()
  finally:
    db.session.close()

  if not error:
    flash(f'Venue {venue.id} was successfully removed!')
  if error:
    flash(f'An error occurred. Venue {venue.id} could not be removed!')
  return None


#  Artists
#  ----------------------------------------------------------------
@app.route('/artists')
def artists():

  data = db.session.query(Artist).all()
  return render_template('pages/artists.html', artists=data)


@app.route('/artists/search', methods=['POST'])
def search_artists():

  data = []
  search_input = request.form.get('search_term', '')
  results_found = db.session.query(Artist).filter(Artist.name.ilike(f'%{search_input}%')).all()  
  results_count = len(results_found)
  
  for result in results_found:
    upcoming_shows_count = len(db.session.query(Show).filter(Show.venue_id==result.id).filter(Show.start_time>datetime.now()).all())
    data.append({
      'id': result.id,
      'name': result.name,
      'num_upcoming_shows': upcoming_shows_count,
    })

  response={
    'count': results_count,
    'data': data,
  }
  return render_template('pages/search_artists.html', results=response, search_term=request.form.get('search_term', ''))


@app.route('/artists/<int:artist_id>')
def show_artist(artist_id):

  artist = Artist.query.get(artist_id)

  if artist:
    upcoming_shows = []
    past_shows = []

    result_upcoming_shows = db.session.query(Show).join(Venue).filter(Show.start_time>datetime.now()).filter(Show.artist_id==artist.id).all()
    for show in result_upcoming_shows:
      upcoming_shows.append({
        'venue_id': show.artist.id,
        'venue_name': show.artist.name,
        'artist_image_link': show.artist.image_link,
        'start_time': show.start_time.strftime('%Y-%m-%d %H:%M:%S'),
      })  
    upcoming_shows_count = len(upcoming_shows)

    result_past_shows = db.session.query(Show).join(Venue).filter(Show.start_time<datetime.now()).filter(Show.artist_id==artist.id).all()
    for show in result_past_shows:
      past_shows.append({
        'venue_id': show.artist.id,
        'venue_name': show.artist.name,
        'artist_image_link': show.artist.image_link,
        'start_time': show.start_time.strftime('%Y-%m-%d %H:%M:%S'),
      })
    past_shows_count = len(past_shows)

    data = {
      'id': artist.id,
      'name': artist.name,
      'genres': artist.genres,
      'city': artist.city,
      'state': artist.state,
      'phone': artist.phone,
      'website': artist.website,
      'facebook_link': artist.facebook_link,
      'seeking_venue': artist.seeking_venue,
      'seeking_description': artist.seeking_description,
      'image_link': artist.image_link,
      'past_shows"': past_shows,   
      'upcoming_shows': upcoming_shows,
      'past_shows_count': past_shows_count,
      'upcoming_shows_count': upcoming_shows_count,
    }
    return render_template('pages/show_artist.html', artist=data)
  return render_tamplate('errors/404.html')


#  Update
#  ----------------------------------------------------------------
@app.route('/artists/<int:artist_id>/edit', methods=['GET'])
def edit_artist(artist_id):

  form = ArtistForm()

  artist_data = Artist.query.get(artist_id)

  if artist_data:
    form.name.data = artist_data.name
    form.genres.data = artist_data.genres
    form.city.data = artist_data.city
    form.state.data = artist_data.state
    form.phone.data = artist_data.phone
    form.website.data = artist_data.website
    form.facebook_link.data = artist_data.facebook_link
    form.seeking_venue.data = artist_data.seeking_venue
    form.seeking_description = artist_data.seeking_description
    form.image_link = artist_data.image_link
  return render_template('forms/edit_artist.html', form=form, artist=artist)


@app.route('/artists/<int:artist_id>/edit', methods=['POST'])
def edit_artist_submission(artist_id):
  
  error = False
  artist_data = Artist.query.get(artist_id)

  try:
    artist_data.name = request.form['name']
    artist_data.genres = request.form.getlist('genres')
    artist_data.city = request.form['city']
    artist_data.state = request.form['state']
    artist_data.phone = request.form['phone']
    artist_data.website = requet.form['website']
    artist_data.facebook_link = request.form['facebook_link']
    artist_data.seeking_venue = request.form['seeking_venue']
    artist_data.seeking_description = request.form['seeking_description']
    artist_data.image_link = request.form['image_link']
    db.session.commit()
  except:
    error = True
    db.session.rollback()
  finally:
    db.session.close()

  if not error:
    flash(f'Artist {artist_data.name} was successfully updated!')
  if error:
    flash(f'An error occurred. Artist {artist_data.name} could not be updated!')
  return redirect(url_for('show_artist', artist_id=artist_id))


@app.route('/venues/<int:venue_id>/edit', methods=['GET'])
def edit_venue(venue_id):
  form = VenueForm()

  venue = Venue.query.get(venue_id)

  if venue:
    form.name.data = venue.name
    form.genres.data = venue.genres
    form.address.data = venue.address
    form.city.data = venue.city
    form.state.data = venue.state
    form.phone.data = venue.phone
    form.website.data = venue.website
    form.facebook_link.data = venue.facebook_link
    form.seeking_venue.data = venue.seeking_venue
    form.seeking_description = venue.seeking_description
    form.image_link = venue.image_link
  return render_template('forms/edit_venue.html', form=form, venue=venue)


@app.route('/venues/<int:venue_id>/edit', methods=['POST'])
def edit_venue_submission(venue_id):
  error = False
  venue = Venue.query.get(venue_id)
  try:
    venue.name = request.form['name']
    venue.genres = request.form.getlist('genres')
    venue.address = request.form['address']
    venue.city = request.form['city']
    venue.state = request.form['state']
    venue.phone = request.form['phone']
    venue.website = requet.form['website']
    venue.facebook_link = request.form['facebook_link']
    venue.seeking_talent = request.form['seeking_talent']
    venue.seeking_description = request.form['seeking_description']
    venue.image_link = request.form['image_link']
    db.session.commit()
  except:
    error = True
    db.session.rollback()
  finally:
    db.session.close()

  if not error:
    flash(f'Venue {venue.name} was successfully updated!')
  if error:
    flash(f'An error occurred. Venue {venue.name} could not be updated!')

  return redirect(url_for('show_venue', venue_id=venue_id))


#  Create Artist
#  ----------------------------------------------------------------

@app.route('/artists/create', methods=['GET'])
def create_artist_form():
  form = ArtistForm()
  return render_template('forms/new_artist.html', form=form)


@app.route('/artists/create', methods=['POST'])
def create_artist_submission():  
  error = False

  try:
    name = request.form['name']
    city = request.form['city']
    state = request.form['state']
    phone = request.form['phone']
    genres = request.form.getlist('genres')
    image_link = request.form['image_link']
    facebook_link = request.form['facebook_link']
    website = request.form['website']
    seeking_venue = True if 'seeking_venue' in request.form else False
    seeking_description = request.form['seeking_description']
    artist = Artist(
      name=name, 
      city=city, 
      state=state, 
      phone=phone, 
      genres=genres, 
      image_link=image_link,
      facebook_link=facebook_link,
      website=website,
      seeking_venue=seeking_venue,
      seeking_description=seeking_description,
    )
    db.session.add(artist)
    db.session.commit()
  except:
    error = True
    db.session.rollback()
  finally:
    db.session.close()

  if not error:
    flash('Artist ' + request.form['name'] + ' was successfully listed!')
  if error:
    flash('An error occurred. Artist ' + request.form['name'] + ' could not be listed.')
  return render_template('pages/home.html')


#  Shows
#  ----------------------------------------------------------------

@app.route('/shows')
def shows():
  shows = db.session.query(Show).join(Artist).join(Venue).all()
  data = []
  for show in shows:
    data.append({
      "venue_id": show.venue.id,
      "venue_name": show.venue.name,
      "artist_id": show.artist_id,
      "artist_name": show.artist.name,
      "artist_image_link": show.artist.image_link,
      "start_time": show.start_time.strftime('%Y-%m-%d %H:%M:%S'),
    })  
  return render_template('pages/shows.html', shows=data)


@app.route('/shows/create')
def create_shows():
  # renders form. do not touch.
  form = ShowForm()
  return render_template('forms/new_show.html', form=form)


@app.route('/shows/create', methods=['POST'])
def create_show_submission():
  error = False

  try:
    artist_id = request.form['artist_id']
    venue_id = request.form['venue_id']
    start_time = request.form['start_time']

    show = Show(artist_id=artist_id, venue_id=venue_id, start_time=start_time)
    db.session.add(show)
    db.session.commit()
  except:
    error = True
    db.session.rollback()
  finally:
    db.session.close()

  if not error:
    flash('Show was successfully listed!')
  if error:
    flash('An error occurred. Show could not be listed')
  return render_template('pages/home.html')

@app.errorhandler(404)
def not_found_error(error):
    return render_template('errors/404.html'), 404

@app.errorhandler(500)
def server_error(error):
    return render_template('errors/500.html'), 500


if not app.debug:
    file_handler = FileHandler('error.log')
    file_handler.setFormatter(
        Formatter('%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]')
    )
    app.logger.setLevel(logging.INFO)
    file_handler.setLevel(logging.INFO)
    app.logger.addHandler(file_handler)
    app.logger.info('errors')

#----------------------------------------------------------------------------#
# Launch.
#----------------------------------------------------------------------------#

# Default port:
if __name__ == '__main__':
    app.run()

# Or specify port manually:
'''
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
'''
