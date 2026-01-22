import pandas as pd
import datetime
from sqlalchemy import text
from nltk.sentiment.vader import SentimentIntensityAnalyzer

# LAZY ANALYZER - creates on first use, auto-downloads
def get_analyzer():
    try:
        analyzer = SentimentIntensityAnalyzer()
        return analyzer
    except LookupError:
        import nltk
        nltk.download('vader_lexicon', quiet=True)
        return SentimentIntensityAnalyzer()

# Replace ALL analyzer.polarity_scores() calls with:
# get_analyzer().polarity_scores(text)
analyzer = get_analyzer()

def init_db(conn):
    """Initializes the database tables and seeds initial data if empty."""
    with conn.session as s:
        # Create strategies table
        s.execute(text('CREATE TABLE IF NOT EXISTS strategies (category TEXT, solution TEXT);'))
        
        # Create mood logs table
        s.execute(text('''
            CREATE TABLE IF NOT EXISTS mood_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date DATE,
                time TIME,
                score REAL
            );
        '''))
        
        # Seed initial strategies if the table is empty
        check = s.execute(text('SELECT COUNT(*) FROM strategies')).fetchone()
        if check[0] == 0:
            seeds = [
                ('Stressed', 'Try the 5-4-3-2-1 grounding technique.'), 
                ('Physical', 'Stretch for 2 minutes.')
            ]
            for cat, sol in seeds:
                s.execute(text('INSERT INTO strategies (category, solution) VALUES (:cat, :sol)'), 
                          params=dict(cat=cat, sol=sol))
        s.commit()

def analyze_mood(text_input):
    """Calculates the compound sentiment score of a string."""
    return analyzer.polarity_scores(text_input)['compound']

def save_mood_to_db(conn, score):
    """Saves the sentiment score with current date and time to the SQL database."""
    with conn.session as s:
        s.execute(text('INSERT INTO mood_logs (date, time, score) VALUES (:d, :t, :s)'),
                  params=dict(
                      d=datetime.date.today(), 
                      t=datetime.datetime.now().strftime("%H:%M:%S"), 
                      s=score
                  ))
        s.commit()

def check_for_crisis(text_input):
    """Scans user input for specific high-risk keywords."""
    red_flags = ["suicide", "harm", "kill", "end my life", "help me die"]
    return any(flag in text_input.lower() for flag in red_flags)

def get_mood_comparison(hist_df):
    """Calculates the difference between current week and last week mood."""
    now = pd.Timestamp.today().normalize()
    current_week_start = now - pd.Timedelta(days=7)
    last_week_start = now - pd.Timedelta(days=14)

    current_week = hist_df[hist_df['date'] >= current_week_start]
    last_week = hist_df[(hist_df['date'] >= last_week_start) & (hist_df['date'] < current_week_start)]

    if not last_week.empty and not current_week.empty:
        return current_week['score'].mean() - last_week['score'].mean()
    return None