import streamlit as st
import pandas as pd
import datetime
import random
import time
from groq import Groq
from utils import init_db, analyze_mood, save_mood_to_db, check_for_crisis
from config import HELPLINES, INSIGHTS, GROQ_API_KEY

# --- 1. SETUP ---
st.set_page_config(page_title="Mind Companion", page_icon="🌱", layout="wide")
conn = st.connection('wellness_db', type='sql', url='sqlite:///wellness.db')
init_db(conn)
client = Groq(api_key=GROQ_API_KEY)

if "messages" not in st.session_state:
    st.session_state.messages = []
if "mood_history" not in st.session_state:
    st.session_state.mood_history = []

# --- 2. SIDEBAR ---
with st.sidebar:
    st.title("📊 Wellbeing Hub")
    
    user_country = st.selectbox("📍 Region:", list(HELPLINES.keys()))
    st.info(f"🆘 {user_country} Helpline: {HELPLINES[user_country]['Number']}")
    
    # Today's Vibe
    with st.expander("✨ Today's Vibe", expanded=True):
        if st.session_state.mood_history:
            # 1. Create DataFrame
            df_today = pd.DataFrame(st.session_state.mood_history)
            
            # 2. FORCE ALL COLUMN NAMES TO LOWERCASE (Ensures 'time' and 'score' match keys)
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
                c1.metric("Current Vibe", "Positive" if latest_score > 0 else "Needs Support")
                c2.metric("Overall Health", f"{wellness_pct}%")
            else:
                st.error(f"Missing columns! Found: {list(df_today.columns)}")
        else:
            st.info("Start chatting to see trends!")

    # Quick Calm Tool
    with st.expander("🧘 Quick Calm"):
        if st.button("Start Breathing Exercise", use_container_width=True):
            status = st.empty()
            bar = st.progress(0)
            for cycle in range(1, 4):
                for i in range(101):
                    status.markdown(f"### 🫁 Inhale... {cycle}/3")
                    bar.progress(i)
                    time.sleep(0.04)
                status.markdown(f"### ✋ Hold...")
                time.sleep(4)
                for i in range(100, -1, -1):
                    status.markdown(f"### 🌬️ Exhale... {cycle}/3")
                    bar.progress(i)
                    time.sleep(0.04)
            status.success("Center reached.")
            bar.empty()

    # Trends (Line Chart Fix)
    with st.expander("📈 Long-term Trends"):
        hist_df = conn.query("SELECT * FROM mood_logs", ttl=0)
        if not hist_df.empty:
            hist_df.columns = [c.lower() for c in hist_df.columns] # Ensure lowercase
            hist_df['date'] = pd.to_datetime(hist_df['date'])
            period = st.radio("Range:", ["7 Days", "30 Days"], horizontal=True)
            days = 7 if period == "7 Days" else 30
            
            cutoff = pd.Timestamp.today().normalize() - pd.Timedelta(days=days)
            filtered = hist_df[hist_df['date'] >= cutoff]
            
            if not filtered.empty:
                # Group by date for a clean daily line
                daily_trend = filtered.groupby(filtered['date'].dt.date)['score'].mean()
                st.line_chart(daily_trend)
                
                csv = hist_df.to_csv(index=False).encode('utf-8')
                st.download_button("📥 Export CSV", csv, "history.csv", use_container_width=True)
            else:
                st.write("No data in this range.")
        else:
            st.write("No logs found.")

# --- 3. MAIN INTERFACE ---
st.title("🌱 Student Mind Companion")

# Optional Onboarding
if "user_name" not in st.session_state:
    with st.chat_message("assistant"):
        st.write("👋 Welcome! I'm your Mind Companion. What should I call you?")
    
    c1, c2 = st.columns([2, 1])
    with c1: name_input = st.text_input("Name:", key="name_box")
    with c2: skip = st.button("Stay Anonymous", use_container_width=True)

    if name_input: st.session_state.user_name = name_input; st.rerun()
    elif skip: st.session_state.user_name = "Friend"; st.rerun()
    st.stop()

# Display Chat History
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# Chat Input Logic
if prompt := st.chat_input("How are you feeling?"):
    st.chat_message("user").markdown(prompt)
    st.session_state.messages.append({"role": "user", "content": prompt})
    
    # 1. Analyze Sentiment
    score = analyze_mood(prompt)
    
    # 2. Update session state (FIXED: Using lowercase 'time' to match chart logic)
    st.session_state.mood_history.append({
        "time": datetime.datetime.now().strftime("%H:%M"), 
        "score": score
    })
    
    # 3. Save to Database (for Long-term Trends)
    save_mood_to_db(conn, score)
    
    # 4. Assistant Response
    with st.chat_message("assistant"):
        if check_for_crisis(prompt):
            h_name = HELPLINES[user_country]['Name']
            h_num = HELPLINES[user_country]['Number']
            resp = f"🚨 **Concerned for you.** Please reach out to **{h_name}** at **{h_num}**."
            st.error(resp)
        else:
            insight = random.choice(INSIGHTS)
            try:
                chat = client.chat.completions.create(
                    model="llama-3.3-70b-versatile",
                    messages=[
                        {"role": "system", "content": f"You are a wellness mentor for {st.session_state.user_name}. Tip: {insight}"},
                        {"role": "user", "content": prompt}
                    ]
                )
                resp = chat.choices[0].message.content
                st.markdown(resp)
                st.caption(f"💡 Research Tip: {insight}")
            except Exception:
                resp = "I'm having a little trouble connecting. Let's try again in a moment."
                st.error(resp)

    st.session_state.messages.append({"role": "assistant", "content": resp})
    st.rerun()