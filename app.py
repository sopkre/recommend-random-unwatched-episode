#!/usr/bin/env python3
"""
Flask app for the episode recommendation tool.
"""

import datetime
import os

from flask import Flask, render_template, request, redirect, url_for
from flask_sqlalchemy import SQLAlchemy

from sqlalchemy import text

ERTOOL_DB_URI = os.environ.get('ERTOOL_DB_URI')

if ERTOOL_DB_URI is None:
    ERTOOL_DB_URI = 'sqlite:///site.db'

print(f"[INFO] DB URI: {ERTOOL_DB_URI}")

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = f'{ERTOOL_DB_URI}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

### -----------------------------------------------------------------

class Series(db.Model):
    """Table for series with relationship to the Season table."""
    __tablename__ = 'series'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(80), nullable=False)
    season = db.relationship("Season", back_populates="series", cascade="all, delete-orphan")

class Season(db.Model):
    """Table for seasons with relationship to the Series and Episode table."""
    __tablename__ = 'season'
    id = db.Column(db.Integer, primary_key=True)
    series_id = db.Column(db.Integer, db.ForeignKey('series.id'), nullable=False)
    season_number = db.Column(db.Integer, nullable=False)
    title = db.Column(db.String(80))
    series = db.relationship("Series", back_populates="season")
    episode = db.relationship("Episode", back_populates="season", cascade="all, delete-orphan")
    __table_args__ = (db.UniqueConstraint("season_number", "series_id"),)

class Episode(db.Model):
    """Table for episodes with relationship to the Season and EpisodeLog table."""
    __tablename__ = 'episode'
    id = db.Column(db.Integer, primary_key=True)
    episode_number = db.Column(db.Integer, nullable=False)
    season_id = db.Column(db.Integer, db.ForeignKey('season.id'), nullable=False)
    title = db.Column(db.String(80))
    season = db.relationship("Season", back_populates="episode")
    episodelog = db.relationship("EpisodeLog", back_populates="episode", cascade="all, delete-orphan")
    __table_args__ = (db.UniqueConstraint("episode_number", "season_id"),)

class EpisodeLog(db.Model):
    """Table for episode logs (e.g. last finish dates) with relationship to the Episode table."""
    __tablename__ = 'episodelog'
    id = db.Column(db.Integer, primary_key=True)
    episode_id = db.Column(db.Integer, db.ForeignKey('episode.id'), nullable=False)
    episode = db.relationship("Episode", back_populates="episodelog")
    date = db.Column(db.DateTime, nullable=False)

### -----------------------------------------------------------------

@app.route('/')
def index():
    """Start page, with overview about series and number of seasons/episodes."""
    count_per_series = db.session.execute(
        text('''
            SELECT COUNT(DISTINCT Episode.id) AS episode_count,
                COUNT(DISTINCT Season.id) AS season_count,
                Series.title as series_title
            FROM Series
            FULL OUTER JOIN Season ON Season.series_id == Series.id
            FULL OUTER JOIN Episode ON Episode.season_id == Season.id
            WHERE Series.title IS NOT NULL
            GROUP BY Series.id
        ''')
        ).all()
    return render_template('index.html', series=count_per_series)


@app.route('/edit_database', methods=['GET'])
def edit_database():
    """Page with options to edit database contents."""
    result = db.session.execute(
        text('''
            SELECT Series.title as series_title,
                Series.id as series_id,
                Season.id as season_id,
                Season.season_number as season_number,
                Episode.id as episode_id,
                Episode.episode_number as episode_number,
                EpisodeLog.id as log_id,
                strftime('%e-%m-%g, %H:%M', EpisodeLog.date) as date
            FROM Episode
            FULL OUTER JOIN EpisodeLog ON EpisodeLog.episode_id == Episode.id
            FULL OUTER JOIN Season ON Episode.season_id == Season.id
            FULL OUTER JOIN Series ON Season.series_id == Series.id
            WHERE Series.title IS NOT NULL
            ORDER BY Series.title, Season.season_number, Episode.episode_number
        ''')
        ).all()

    return render_template(('edit_database.html'), episode_logs=result)


@app.route('/get_random_episode', methods=['GET', 'POST'])
def get_random_episode():
    """Page to request random episode recommendation; includes listing of all logs."""
    series_in_db = db.session.execute(
        text('''
            SELECT id, title
            FROM Series
            ORDER BY title
        ''')
        ).all()

    episode_logs = db.session.execute(
        text('''
            SELECT Series.title as series_title,
                Series.id as series_id,
                Season.id as season_id,
                Season.season_number as season_number,
                Episode.id as episode_id,
                Episode.episode_number as episode_number,
                EpisodeLog.id as log_id,
                strftime('%e-%m-%g, %H:%M', EpisodeLog.date) as date
            FROM Episode
            INNER JOIN EpisodeLog ON EpisodeLog.episode_id == Episode.id
            INNER JOIN Season ON Episode.season_id == Season.id
            INNER JOIN Series ON Season.series_id == Series.id
            ORDER BY Series.title, Season.season_number, Episode.episode_number
        ''')
        ).all()

    last_log_options = {"never" : "1", "at least 6 months ago" : "2", "irrelevant" : "3"}

    if request.method == 'GET':
        return render_template(('get_random_episode.html'),
            available_series=series_in_db,
            last_log_options=last_log_options,
            return_val=None,
            joined_episodes=episode_logs)

    if request.method == 'POST':

        selected_last_log_option = request.form["last_log_option"]
        assert selected_last_log_option not in last_log_options

        date_string = ''
        if selected_last_log_option == last_log_options["never"]:
            date_string = '1880-01-01'
        elif selected_last_log_option == last_log_options["at least 6 months ago"]:
            six_months_ago = datetime.datetime.now() - datetime.timedelta(days=6*30)
            date_string = six_months_ago.strftime('%Y-%m-%d %H:%M')
        elif selected_last_log_option == last_log_options["irrelevant"]:
            date_string = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        else:
            pass

        series_id = request.form['series_id']

        selected_episode = db.session.execute(
            text('''
                SELECT Series.title as series_title,
                    Series.id as series_id,
                    Season.id as season_id,
                    Season.season_number as season_number,
                    Episode.id as episode_id,
                    Episode.episode_number as episode_number,
                    EpisodeLog.id as log_id,
                    EpisodeLog.date as date
                FROM Episode
                FULL OUTER JOIN EpisodeLog ON EpisodeLog.episode_id == Episode.id
                INNER JOIN Season ON Episode.season_id == Season.id
                INNER JOIN Series ON Season.series_id == Series.id
                WHERE (Season.series_id == :series_id)
                AND (EpisodeLog.id is null OR EpisodeLog.date < datetime(:date_string))
                ORDER BY RANDOM()
                LIMIT 1
            '''),
            {'series_id' : series_id,
            'date_string' : date_string}
            ).all()

        if len(selected_episode) > 0:
            return_val = "success"
            selected_episode = selected_episode[0]
        else:
            return_val = "empty"
            selected_episode = None

        return render_template(('get_random_episode.html'),
            available_series=series_in_db,
            last_log_options=last_log_options,
            return_val=return_val,
            selected_episode=selected_episode,
            joined_episodes=episode_logs)

### ---------------------- POST Actions ----------------------------------

@app.route('/add_series', methods=['POST'])
def add_series():
    """Method to add series to the database."""
    title = request.form['title']
    new_series = Series(title=title)
    db.session.add(new_series)
    db.session.commit()
    return redirect(url_for('edit_database'))


@app.route('/add_season', methods=['POST'])
def add_season():
    """Method to add seasons to the database."""
    series_id = request.form['series_id']
    season_number = request.form['season_number']
    number_of_episodes = request.form['number_of_episodes']

    new_season = Season(series_id=series_id,season_number=season_number)
    db.session.add(new_season)
    db.session.commit()

    for n in range(int(number_of_episodes)):
        episode = Episode(season_id=new_season.id, episode_number=n+1)
        db.session.add(episode)
        db.session.commit()
    return redirect(url_for('edit_database'))


@app.route('/add_episode', methods=['POST'])
def add_episode():
    """Method to add episodes to the database."""
    series_id = request.form['series_id']
    season_number = request.form['season_number']
    episode_number = request.form['episode_number']

    episode = db.session.execute(
        text('''SELECT *
            FROM Episode
            FULL OUTER JOIN Season ON Episode.season_id == Season.id
            FULL OUTER JOIN Series ON Season.series_id == Series.id
            WHERE Series.id == :series_id
            AND Season.season_number == :season_number
            AND Episode.episode_number == :episode_number
            '''),
        {'season_number' : season_number,
        'series_id' : series_id,
        'episode_number' : episode_number}
        ).all()

    if len(episode) != 0:
        return redirect(url_for('edit_database'))

    season = db.session.execute(
        text('''
            SELECT Season.id as season_id, Season.season_number as season_number
            FROM Season
            WHERE Season.series_id == :series_id
            AND Season.season_number == :season_number
        '''),
        {'season_number' : season_number,
        'series_id' : series_id}
        ).all()

    if len(season) == 0:
        new_season = Season(series_id=series_id,season_number=season_number)
        db.session.add(new_season)
        db.session.commit()
        season_id = new_season.id
    else:
        season_id = season[0].season_id

    new_episode = Episode(season_id=season_id,episode_number=episode_number)
    db.session.add(new_episode)
    db.session.commit()
    return redirect(url_for('edit_database'))

@app.route('/add_episode_log/<location>/<int:episode_id>', methods=['POST'])
def add_episode_log(location, episode_id):
    """Page to add log for episode, timestamp is now."""
    new_episode_log = EpisodeLog(episode_id=episode_id,date=datetime.datetime.now())
    db.session.add(new_episode_log)
    db.session.commit()
    return redirect(url_for(location))


@app.route('/delete_series/<int:series_id>', methods=['POST'])
def delete_series(series_id):
    """Method to delete series from database."""
    series = Series.query.get_or_404(series_id)
    db.session.delete(series)
    db.session.commit()
    return redirect(url_for('edit_database'))


@app.route('/delete_season/<int:season_id>', methods=['POST'])
def delete_season(season_id):
    """Method to delete season from database."""
    season = Season.query.get_or_404(season_id)
    db.session.delete(season)
    db.session.commit()
    return redirect(url_for('edit_database'))


@app.route('/delete_episode/<int:episode_id>', methods=['POST'])
def delete_episode(episode_id):
    """Method to delete episode from database."""
    episode = Episode.query.get_or_404(episode_id)
    db.session.delete(episode)
    db.session.commit()
    return redirect(url_for('edit_database'))


@app.route('/delete_episode_log/<location>/<int:log_id>', methods=['POST'])
def delete_episode_log(location, log_id):
    """Method to delete episode log from database."""
    log = EpisodeLog.query.get_or_404(log_id)
    db.session.delete(log)
    db.session.commit()
    return redirect(url_for(location))




if __name__ == '__main__':
    with app.app_context():
        db.create_all()  # Create the database tables
    app.run(debug=True)
