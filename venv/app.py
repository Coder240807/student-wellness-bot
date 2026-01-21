import streamlit as st
import pandas as pd
import random
import datetime
import nltk
from nltk.sentiment.vader import SentimentIntensityAnalyzer
from sqlalchemy import text
from groq import Groq
from config import HELPLINES, INSIGHTS 
import time

# --- 1. CONFIGURATION & SETUP ---
st.set_page_config(page_title="Mind Companion", page_icon="🌱", layout="wide")

# Initialize AI
client = Groq(api_key="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") 
nltk.download('vader_lexicon', quiet=True)
analyzer = SentimentIntensityAnalyzer()

conn = st.connection('wellness_db', type='sql', url='sqlite:///wellness.db')

if "messages" not in st.session_state:
    st.session_state.messages = []
if "mood_history" not in st.session_state:
    st.session_state.mood_history = []

# --- 2. DATABASE INITIALIZATION ---
def init_db():
    with conn.session as s:
        s.execute(text('CREATE TABLE IF NOT EXISTS strategies (category TEXT, solution TEXT);'))
        s.execute(text('''
            CREATE TABLE IF NOT EXISTS mood_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date DATE,
                time TIME,
                score REAL
            );
        '''))
        check = s.execute(text('SELECT COUNT(*) FROM strategies')).fetchone()
        if check[0] == 0:
            seeds = [('Stressed', 'Try the 5-4-3-2-1 grounding technique.'), ('Physical', 'Stretch for 2 minutes.')]
            for cat, sol in seeds:
                s.execute(text('INSERT INTO strategies (category, solution) VALUES (:cat, :sol)'), params=dict(cat=cat, sol=sol))
        s.commit()

init_db()

# --- 3. HELPER FUNCTIONS ---
def check_for_crisis(text):
    red_flags = ["suicide", "harm", "kill", "end my life", "help me die"]
    return any(flag in text.lower() for flag in red_flags)

# --- 4. SIDEBAR ---
with st.sidebar:
    st.title("📊 Wellbeing Hub")
    
    # Country Selector
    user_country = st.selectbox("📍 Select your region:", list(HELPLINES.keys()))
    st.info(f"🆘 {user_country} Helpline: {HELPLINES[user_country]['Number']}")
    
   # Today's Vibe
    with st.expander("✨ Today's Vibe", expanded=True):
        if st.session_state.mood_history:
            # 1. Create DataFrame
            df_today = pd.DataFrame(st.session_state.mood_history)
            
            # 2. FORCE ALL COLUMN NAMES TO LOWERCASE (Fixes the KeyError)
            df_today.columns = [c.lower() for c in df_today.columns]
            
            # 3. Double check the columns exist before charting
            if "time" in df_today.columns and "score" in df_today.columns:
                # Prepare data for the chart
                chart_data = df_today.set_index("time")[["score"]]
                
                # REAL-TIME COLOR: Based on the very last message
                latest_score = df_today['score'].iloc[-1]
                
                if latest_score < -0.1:
                    chart_color = "#e74c3c"  # Red
                elif latest_score > 0.1:
                    chart_color = "#2ecc71"  # Green
                else:
                    chart_color = "#f1c40f"  # Yellow
                
                st.area_chart(chart_data, color=chart_color)
                
                # Metrics
                avg_today = df_today['score'].mean()
                wellness_pct = int(((avg_today + 1) / 2) * 100)
                
                c1, c2 = st.columns(2)
                c1.metric("Current Vibe", "Good" if latest_score > 0 else "Needs Support")
                c2.metric("Overall Wellness", f"{wellness_pct}%")
            else:
                st.error(f"Missing columns! Found: {list(df_today.columns)}")
        else:
            st.info("Start chatting to see trends!")

    st.divider()
    st.subheader("🧘 Quick Calm")
    
    if st.button("Start Breathing Exercise", use_container_width=True):
        status_text = st.empty()
        progress_bar = st.progress(0)
        for cycle in range(1, 4):
            for i in range(101):
                status_text.markdown(f"### 🫁 Inhale... {cycle}/3")
                progress_bar.progress(i)
                time.sleep(0.04) 
            status_text.markdown(f"### ✋ Hold... {cycle}/3")
            time.sleep(4)
            for i in range(100, -1, -1):
                status_text.markdown(f"### 🌬️ Exhale... {cycle}/3")
                progress_bar.progress(i)
                time.sleep(0.04) 
            status_text.markdown(f"### ☁️ Rest...")
            time.sleep(2)
        status_text.success("Center reached.")
        progress_bar.empty()

    # DROPDOWN 2: Long-term Trends
    with st.expander("📈 Long-term Trends", expanded=False):
        hist_df = conn.query("SELECT * FROM mood_logs")
        if not hist_df.empty:
            hist_df['date'] = pd.to_datetime(hist_df['date'])
            period = st.radio("Range:", ["7 Days", "30 Days"], horizontal=True)
            today_ts = pd.Timestamp.today().normalize()
            
            if period == "7 Days":
                filtered = hist_df[hist_df['date'] >= (today_ts - pd.Timedelta(days=7))]
            else:
                filtered = hist_df[hist_df['date'] >= (today_ts - pd.Timedelta(days=30))]
            
            if not filtered.empty:
                daily_trend = filtered.groupby(filtered['date'].dt.date)['score'].mean()
                h_avg = daily_trend.mean()
                h_color = "#27ae60" if h_avg >= 0 else "#c0392b"
                st.line_chart(daily_trend, color=h_color)

                # --- MOOD COMPARISON INSIGHT ---
                now = pd.Timestamp.today().normalize()
                current_week_df = hist_df[(hist_df['date'] >= (now - pd.Timedelta(days=7)))]
                last_week_df = hist_df[(hist_df['date'] >= (now - pd.Timedelta(days=14))) & (hist_df['date'] < (now - pd.Timedelta(days=7)))]

                if not last_week_df.empty and not current_week_df.empty:
                    diff = current_week_df['score'].mean() - last_week_df['score'].mean()
                    st.divider()
                    if diff > 0.05:
                        st.success(f"🌟 Mood up {abs(diff)*50:.0f}% from last week!")
                    elif diff < -0.05:
                        st.warning(f"📉 Mood down {abs(diff)*50:.0f}% from last week.")
                    else:
                        st.info("⚖️ Mood is steady.")

                st.divider()
                csv = hist_df.to_csv(index=False).encode('utf-8')
                st.download_button("📥 Export Report", csv, "mood_history.csv", use_container_width=True)
            else:
                st.write("Not enough data.")
        else:
            st.write("No logs yet.")

    with st.expander("🛠️ Admin Settings"):
        pwd = st.text_input("Admin Key", type="password")
        if pwd == "admin123":
            n_cat = st.selectbox("Type", ["Breathing", "Physical", "Mental", "Stressed"])
            n_tip = st.text_area("New Tip")
            if st.button("Save to DB"):
                if n_tip:
                    with conn.session as s:
                        s.execute(text('INSERT INTO strategies (category, solution) VALUES (:c, :s)'), params=dict(c=n_cat, s=n_tip))
                        s.commit()
                    st.toast("Saved!")

# --- 5. MAIN CHAT INTERFACE ---
st.title("🌱 Student Mind Companion")

# Optional Onboarding
if "user_name" not in st.session_state:
    with st.chat_message("assistant"):
        st.write("👋 Hello! I'm your Mind Companion. Would you like to tell me your name, or stay anonymous?")
    
    col1, col2 = st.columns([2, 1])
    with col1:
        name_input = st.text_input("Enter name:", key="name_box")
    with col2:
        skip_button = st.button("Stay Anonymous", use_container_width=True)

    if name_input:
        st.session_state.user_name = name_input
        st.rerun()
    elif skip_button:
        st.session_state.user_name = "Friend"
        st.rerun()
    
    st.stop()

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

if prompt := st.chat_input("How are you feeling today?"):
    with st.chat_message("user"):
        st.markdown(prompt)
    st.session_state.messages.append({"role": "user", "content": prompt})
    
    score = analyzer.polarity_scores(prompt)['compound']
    st.session_state.mood_history.append({"Time": datetime.datetime.now().strftime("%H:%M"), "Score": score})
    
    with st.chat_message("assistant"):
        if check_for_crisis(prompt):
            local_name = HELPLINES[user_country]['Name']
            local_num = HELPLINES[user_country]['Number']
            resp = f"🚨 **Concerned for you.** Contact **{local_name}** at **{local_num}**."
            st.error(resp)
        else:
            selected_insight = random.choice(INSIGHTS)
            try:
                chat_comp = client.chat.completions.create(
                    model="llama-3.3-70b-versatile",
                    messages=[
                        {"role": "system", "content": f"You are a wellness mentor talking to {st.session_state.user_name}. Research: {selected_insight}"},
                        {"role": "user", "content": prompt}
                    ]
                )
                resp = chat_comp.choices[0].message.content
                st.markdown(resp)
                st.caption(f"💡 Research Tip: {selected_insight}")
            except:
                resp = "I'm resting. Please try again!"
                st.error(resp)

    # Permanent Database Save
    with conn.session as s:
        s.execute(text('INSERT INTO mood_logs (date, time, score) VALUES (:d, :t, :s)'),
                  params=dict(d=datetime.date.today(), t=datetime.datetime.now().strftime("%H:%M:%S"), s=score))
        s.commit()

    st.session_state.messages.append({"role": "assistant", "content": resp})
    st.rerun()