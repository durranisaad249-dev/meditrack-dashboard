# ============================================================
#  MediTrack A+ v3.0 — Industry-Level Analytics Dashboard
#  16 Pages including 7 new features + upgraded doctor avatars
# ============================================================

import os, time, pickle, smtplib, io, random
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta

import pandas as pd
import numpy as np
import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import folium
from streamlit_folium import st_folium

try:
    from fpdf import FPDF
    FPDF_OK = True
except ImportError:
    FPDF_OK = False

try:
    import shap
    SHAP_OK = True
except ImportError:
    SHAP_OK = False

# ── Page config ─────────────────────────────────────────────
st.set_page_config(
    page_title="MediTrack A+ v3",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Global CSS ───────────────────────────────────────────────
st.markdown("""
<style>
html,body,[class*="css"]{font-family:'Segoe UI',sans-serif;}
[data-testid="stMetricValue"]{font-size:1.55rem!important;font-weight:800!important;color:#1a73e8!important;}
[data-testid="stMetricLabel"]{font-size:.78rem!important;color:#666!important;}
.section-header{background:linear-gradient(90deg,#1a73e8,#0d47a1);color:white;
  padding:10px 18px;border-radius:10px;margin-bottom:14px;font-weight:700;font-size:1rem;}
.insight-box{background:linear-gradient(135deg,#fff9e6,#fff3cc);border-left:4px solid #f5a623;
  border-radius:0 10px 10px 0;padding:12px 16px;margin:8px 0;font-size:.88rem;color:#5a3e00;}
.reminder-card{background:white;border-radius:12px;border:1px solid #e0e7ff;
  padding:14px 18px;margin-bottom:10px;box-shadow:0 2px 6px rgba(0,0,0,.05);}
.doc-name{font-size:1.1rem;font-weight:700;color:#1a2332;margin:0 0 2px 0;}
.doc-spec{font-size:.85rem;color:#1a73e8;font-weight:600;margin:0 0 6px 0;}
.doc-meta{font-size:.8rem;color:#555;line-height:1.8;}
.profile-card{background:linear-gradient(135deg,#f0f4ff,#e8f0fe);border:1px solid #d0e0ff;
  border-radius:14px;padding:20px;margin-bottom:16px;}
.booking-success{background:#e8f5e9;border:1px solid #4caf50;border-radius:10px;
  padding:16px;text-align:center;font-weight:600;color:#1b5e20;}
[data-testid="stSidebar"]{background:linear-gradient(180deg,#0d1b2a 0%,#1a2f4a 100%)!important;}
[data-testid="stSidebar"] *{color:#c8d8e8!important;}
</style>
""", unsafe_allow_html=True)

# ── Constants ────────────────────────────────────────────────
REMINDER_LOG  = 'reminder_log.csv'
BOOKINGS_FILE = 'meditrack_data.csv'
GOALS_DEFAULTS = {'revenue': 6000000, 'no_show_cap': 15.0, 'appointments': 2000}
FEATURE_NAMES = ['City','Department','Doctor','Returning','Hour','Day of Week','Month']

CITIES = ['Karachi','Lahore','Islamabad','Peshawar','Multan']
DEPARTMENTS = ['General','Cardiology','Ortho','Dermatology','Pediatrics','MBBS','Physiotherapy']
DOCTOR_MAP = {
    'Dr.Hammad': 'Physiotherapist',
    'Dr.Saad':   'MBBS Specialist',
    'Dr.Aleena': 'Cardiologist',
    'Dr.Maryam': 'Neurologist',
}

# ── Doctor avatar config (best styles) ──────────────────────
DOCTOR_INFO = [
    {
        'name': 'Dr. Hammad', 'key': 'Dr.Hammad',
        'spec': 'Physiotherapist', 'dept': 'Physiotherapy',
        'exp': '8 Years', 'timing': '9 AM – 2 PM',
        'edu': 'DPT — University of Health Sciences, Lahore',
        'color': '#e8f4fd', 'border': '#1a73e8',
        # adventurer = best masculine illustrated avatar style
        'img': 'https://api.dicebear.com/7.x/adventurer/svg?seed=Hammad2025&backgroundColor=b6e3f4,c8d9f0&radius=50',
    },
    {
        'name': 'Dr. Saad', 'key': 'Dr.Saad',
        'spec': 'MBBS Specialist', 'dept': 'General / MBBS',
        'exp': '12 Years', 'timing': '10 AM – 5 PM',
        'edu': 'MBBS — King Edward Medical University, Lahore',
        'color': '#f0eeff', 'border': '#6c5ce7',
        # adventurer with different seed for distinct look
        'img': 'https://api.dicebear.com/7.x/adventurer/svg?seed=Saad2025&backgroundColor=c0aede,d4c5f0&radius=50',
    },
    {
        'name': 'Dr. Aleena', 'key': 'Dr.Aleena',
        'spec': 'Cardiologist', 'dept': 'Cardiology',
        'exp': '10 Years', 'timing': '9 AM – 3 PM',
        'edu': 'FCPS Cardiology — CPSP, Islamabad',
        'color': '#fff0f3', 'border': '#e84393',
        # lorelei = most beautiful feminine illustrated avatar
        'img': 'https://api.dicebear.com/7.x/lorelei/svg?seed=Aleena2025&backgroundColor=ffd5dc,ffbdcf&radius=50',
    },
    {
        'name': 'Dr. Maryam', 'key': 'Dr.Maryam',
        'spec': 'Neurologist', 'dept': 'Neurology',
        'exp': '7 Years', 'timing': '11 AM – 6 PM',
        'edu': 'FCPS Neurology — Aga Khan University, Karachi',
        'color': '#f0fff4', 'border': '#00b894',
        # lorelei with different seed & color for distinct look
        'img': 'https://api.dicebear.com/7.x/lorelei/svg?seed=Maryam2025&backgroundColor=d1f4cc,b8edbc&radius=50',
    },
]

# ── Data loader ──────────────────────────────────────────────
@st.cache_data
def load_data():
    df = pd.read_csv(BOOKINGS_FILE)
    df['appointment_date'] = pd.to_datetime(df['appointment_date'])
    df['month']       = df['appointment_date'].dt.month
    df['month_name']  = df['appointment_date'].dt.strftime('%b')
    df['day']         = df['appointment_date'].dt.day_name()
    df['day_of_week'] = df['appointment_date'].dt.dayofweek
    df['week_num']    = df['appointment_date'].dt.isocalendar().week.astype(int)
    return df

# ── Model loader ─────────────────────────────────────────────
@st.cache_resource
def load_model():
    model     = pickle.load(open('model.pkl',     'rb'))
    le_city   = pickle.load(open('le_city.pkl',   'rb'))
    le_dept   = pickle.load(open('le_dept.pkl',   'rb'))
    le_doctor = pickle.load(open('le_doctor.pkl', 'rb'))
    return model, le_city, le_dept, le_doctor

# ── SHAP explainer ───────────────────────────────────────────
@st.cache_resource
def load_shap_explainer(_model):
    if not SHAP_OK:
        return None
    return shap.TreeExplainer(_model)

# ── Reminder helpers ─────────────────────────────────────────
def load_reminder_log():
    if os.path.exists(REMINDER_LOG):
        return pd.read_csv(REMINDER_LOG)
    return pd.DataFrame(columns=[
        'patient_id','patient_name','email','phone',
        'sent_at','channel','risk_score','risk_level',
        'doctor','department','city','message_type'
    ])

def save_reminders(rows: pd.DataFrame, channel: str, message_type: str = 'Standard'):
    log = load_reminder_log()
    new_rows = []
    for _, r in rows.iterrows():
        new_rows.append({
            'patient_id':   r['patient_id'],
            'patient_name': r['patient_name'],
            'email':        r.get('email', ''),
            'phone':        r.get('phone', ''),
            'sent_at':      datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'channel':      channel,
            'risk_score':   r.get('risk_score', 0),
            'risk_level':   r.get('Risk Level', ''),
            'doctor':       r.get('doctor', ''),
            'department':   r.get('department', ''),
            'city':         r.get('city', ''),
            'message_type': message_type,
        })
    log = pd.concat([log, pd.DataFrame(new_rows)], ignore_index=True)
    log.to_csv(REMINDER_LOG, index=False)

# ── Smart message generator ──────────────────────────────────
def generate_smart_message(patient_name, doctor, department, risk_score,
                            appointment_date, hour, is_returning, city):
    time_str = f"{hour}:00 {'AM' if hour < 12 else 'PM'}"
    date_str = pd.to_datetime(appointment_date).strftime('%A, %d %b %Y') \
               if appointment_date is not None else 'your upcoming appointment date'
    greeting = "Welcome back," if is_returning else "Dear"
    if risk_score >= 60:
        return (f"URGENT REMINDER\n\n{greeting} {patient_name},\n\n"
                f"Your appointment with {doctor} ({department}) is scheduled for "
                f"{date_str} at {time_str} — {city} Clinic.\n\n"
                f"Our records suggest patients with your profile sometimes miss appointments. "
                f"Please CONFIRM by replying YES, or call 0300-0000000 to reschedule.\n\n"
                f"Missing without notice may delay your treatment.\n\n— MediTrack Team")
    elif risk_score >= 35:
        return (f"Appointment Reminder\n\n{greeting} {patient_name},\n\n"
                f"Friendly reminder of your appointment with {doctor} ({department}) "
                f"on {date_str} at {time_str} — {city} Clinic.\n\n"
                f"Please arrive 10 minutes early. To reschedule, call 0300-0000000.\n\n— MediTrack Team")
    else:
        return (f"Appointment Confirmed\n\n{greeting} {patient_name},\n\n"
                f"Your appointment with {doctor} ({department}) is all set "
                f"for {date_str} at {time_str} — {city} Clinic.\n\nSee you soon! — MediTrack Team")

# ── PDF report generator ─────────────────────────────────────
def generate_pdf(df):
    if not FPDF_OK:
        return None

    class MediTrackPDF(FPDF):
        def header(self):
            self.set_fill_color(26, 115, 232)
            self.rect(0, 0, 210, 28, 'F')
            self.set_y(5)
            self.set_font('Helvetica', 'B', 16)
            self.set_text_color(255, 255, 255)
            self.cell(0, 10, 'MediTrack A+  —  Management Report', align='C', new_x='LMARGIN', new_y='NEXT')
            self.set_font('Helvetica', '', 9)
            self.cell(0, 8, f'Generated: {datetime.now().strftime("%d %b %Y  %H:%M")}', align='C', new_x='LMARGIN', new_y='NEXT')
            self.ln(4)

        def footer(self):
            self.set_y(-15)
            self.set_font('Helvetica', 'I', 8)
            self.set_text_color(150)
            self.cell(0, 10, f'Page {self.page_no()} | MediTrack A+ Healthcare Intelligence Platform', align='C')

        def section_title(self, title):
            self.set_fill_color(26, 115, 232)
            self.set_text_color(255, 255, 255)
            self.set_font('Helvetica', 'B', 11)
            self.cell(0, 9, f'   {title}', fill=True, new_x='LMARGIN', new_y='NEXT')
            self.set_text_color(0)
            self.ln(3)

        def kpi_row(self, label, value):
            self.set_font('Helvetica', 'B', 10)
            self.set_fill_color(240, 245, 255)
            self.cell(80, 7, f'  {label}', border='B', fill=True)
            self.set_font('Helvetica', '', 10)
            self.set_fill_color(255, 255, 255)
            self.cell(0, 7, f'  {value}', border='B', fill=True, new_x='LMARGIN', new_y='NEXT')

        def add_df_table(self, headers, rows, col_widths):
            self.set_fill_color(26, 115, 232)
            self.set_text_color(255, 255, 255)
            self.set_font('Helvetica', 'B', 9)
            for i, h in enumerate(headers):
                self.cell(col_widths[i], 7, f' {h}', border=1, fill=True)
            self.ln()
            self.set_text_color(0)
            for j, row in enumerate(rows):
                self.set_fill_color(248, 250, 255) if j % 2 == 0 else self.set_fill_color(255, 255, 255)
                self.set_font('Helvetica', '', 9)
                for i, cell in enumerate(row):
                    self.cell(col_widths[i], 7, f' {cell}', border=1, fill=True)
                self.ln()
            self.ln(4)

    pdf = MediTrackPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()

    # ── KPI Section ──
    total_rev   = df['fee'].sum()
    earned_rev  = df[df['status']=='Completed']['fee'].sum()
    lost_rev    = df[df['status']=='No-show']['fee'].sum()
    noshow_rate = (df['status']=='No-show').mean()*100
    comp_rate   = (df['status']=='Completed').mean()*100
    total_appts = len(df)
    uniq_pts    = df['patient_name'].nunique()
    ret_rate    = df['returning'].mean()*100
    recovery    = lost_rev * 0.5

    pdf.section_title('CLINIC OVERVIEW — KEY PERFORMANCE INDICATORS')
    pdf.kpi_row('Total Revenue (All)',      f'Rs {total_rev:,}')
    pdf.kpi_row('Revenue Earned',           f'Rs {earned_rev:,}')
    pdf.kpi_row('Revenue Lost (No-shows)',  f'Rs {lost_rev:,}')
    pdf.kpi_row('50% Recovery Potential',   f'Rs {recovery:,.0f}')
    pdf.kpi_row('Total Appointments',       f'{total_appts:,}')
    pdf.kpi_row('Unique Patients',          f'{uniq_pts:,}')
    pdf.kpi_row('Completion Rate',          f'{comp_rate:.1f}%')
    pdf.kpi_row('No-show Rate',             f'{noshow_rate:.1f}%')
    pdf.kpi_row('Returning Patient Rate',   f'{ret_rate:.1f}%')
    pdf.ln(4)

    # ── Department Section ──
    dept = df.groupby('department').agg(
        Appointments = ('patient_id','count'),
        Revenue      = ('fee','sum'),
        NoShow_Rate  = ('status', lambda x: (x=='No-show').mean()*100),
        Comp_Rate    = ('status', lambda x: (x=='Completed').mean()*100),
    ).reset_index().sort_values('NoShow_Rate', ascending=False)

    pdf.section_title('DEPARTMENT PERFORMANCE')
    pdf.add_df_table(
        ['Department', 'Appointments', 'Revenue', 'No-show %', 'Completion %'],
        [(r['department'], str(r['Appointments']),
          f"Rs {r['Revenue']:,}", f"{r['NoShow_Rate']:.1f}%", f"{r['Comp_Rate']:.1f}%")
         for _, r in dept.iterrows()],
        [50, 35, 45, 30, 30]
    )

    # ── Doctor Section ──
    doc = df.groupby(['doctor','specialization']).agg(
        Appointments = ('patient_id','count'),
        Revenue      = ('fee','sum'),
        NoShow_Rate  = ('status', lambda x: (x=='No-show').mean()*100),
    ).reset_index().sort_values('NoShow_Rate', ascending=False)

    pdf.section_title('DOCTOR PERFORMANCE')
    pdf.add_df_table(
        ['Doctor', 'Specialization', 'Appointments', 'Revenue', 'No-show %'],
        [(r['doctor'], r['specialization'], str(r['Appointments']),
          f"Rs {r['Revenue']:,}", f"{r['NoShow_Rate']:.1f}%")
         for _, r in doc.iterrows()],
        [38, 42, 32, 42, 30]
    )

    # ── City Section ──
    city = df.groupby('city').agg(
        Revenue     = ('fee','sum'),
        Appointments= ('patient_id','count'),
        NoShow_Rate = ('status', lambda x: (x=='No-show').mean()*100),
    ).reset_index().sort_values('Revenue', ascending=False)

    pdf.section_title('CITY REVENUE SUMMARY')
    pdf.add_df_table(
        ['City', 'Revenue', 'Appointments', 'No-show %'],
        [(r['city'], f"Rs {r['Revenue']:,}", str(r['Appointments']), f"{r['NoShow_Rate']:.1f}%")
         for _, r in city.iterrows()],
        [45, 55, 45, 35]
    )

    # ── Insight Box ──
    pdf.set_fill_color(255, 249, 230)
    pdf.set_draw_color(245, 166, 35)
    pdf.set_font('Helvetica', 'B', 10)
    pdf.set_text_color(90, 62, 0)
    worst_dept = dept.iloc[0]['department']
    worst_loss = df[(df['status']=='No-show') & (df['department']==worst_dept)]['fee'].sum()
    best_city  = city.iloc[0]['city']
    pdf.multi_cell(0, 7,
        f'  MANAGEMENT INSIGHT: {worst_dept} has the highest no-show rate. '
        f'Directing Smart Reminders at {worst_dept} patients could recover Rs {worst_loss//2:,} annually. '
        f'{best_city} is your highest-revenue clinic location.',
        border=1, fill=True)

    pdf.set_text_color(0)
    pdf.set_draw_color(0)
    return bytes(pdf.output())

# ── Session state init ────────────────────────────────────────
if 'goals' not in st.session_state:
    st.session_state.goals = GOALS_DEFAULTS.copy()

# ── Load everything ──────────────────────────────────────────
df = load_data()
model, le_city, le_dept, le_doctor = load_model()
shap_explainer = load_shap_explainer(model)

# ── Sidebar navigation ───────────────────────────────────────
st.sidebar.markdown("""
<div style='text-align:center;padding:20px 10px 10px;'>
  <div style='font-size:2.2rem;'>🏥</div>
  <div style='font-size:1.2rem;font-weight:800;color:#fff;letter-spacing:.5px;'>MediTrack A+</div>
  <div style='font-size:.7rem;color:#8aacc8;margin-top:2px;'>Healthcare Intelligence Platform v3.0</div>
</div>
<hr style='border-color:#2a4060;margin:10px 0;'>
<div style='font-size:.68rem;color:#5a7a9a;padding:0 8px 4px;'>ANALYTICS</div>
""", unsafe_allow_html=True)

page = st.sidebar.radio("", [
    "📊 Overview Dashboard",
    "🏥 Department Analysis",
    "👨‍⚕️ Doctor Performance",
    "🗺️ City Revenue",
    "👤 Patient Profile",
    "📅 Book Appointment",
    "🧠 Smart Reminders",
    "📈 Reminder Analytics",
    "🔮 No-Show Predictor",
    "📉 Revenue Forecast",
    "💡 Revenue Intelligence",
    "🎯 KPI Goals",
    "🩺 Our Doctors",
    "🗓️ Schedule Heatmap",
    "🗺️ Pakistan Clinic Map",
    "📄 PDF Reports",
])

st.sidebar.markdown(f"""
<hr style='border-color:#2a4060;margin:12px 0;'>
<div style='font-size:.7rem;color:#6a8faf;line-height:1.9;'>
📅 {df['appointment_date'].min().date()} → {df['appointment_date'].max().date()}<br>
🗂️ {len(df):,} total records<br>
🔄 Updated: {datetime.now().strftime('%d %b %Y')}
</div>
<hr style='border-color:#2a4060;margin:12px 0;'>
<div style='text-align:center;font-size:.65rem;color:#3a6080;'>
© 2025 MediTrack A+ v3.0<br>Built with Streamlit
</div>
""", unsafe_allow_html=True)


# ============================================================
# PAGE 1 — OVERVIEW DASHBOARD
# ============================================================
if page == "📊 Overview Dashboard":
    st.title("🏥 MediTrack A+ — Management Overview")
    st.caption("Real-time operational snapshot for clinic leadership.")

    total_rev   = df['fee'].sum()
    noshow_rate = (df['status']=='No-show').mean()*100
    comp_rate   = (df['status']=='Completed').mean()*100
    cancel_rate = (df['status']=='Cancelled').mean()*100
    ret_pct     = df['returning'].mean()*100
    rev_lost    = df[df['status']=='No-show']['fee'].sum()
    avg_fee     = df['fee'].mean()

    k1,k2,k3,k4 = st.columns(4)
    k1.metric("💰 Total Revenue",      f"Rs {total_rev:,}",  f"Avg Rs {avg_fee:,.0f}/appt")
    k2.metric("📅 Total Appointments", f"{len(df):,}",        f"✅ {comp_rate:.1f}% completed")
    k3.metric("⚠️ No-show Rate",       f"{noshow_rate:.1f}%", f"Rs {rev_lost:,} lost")
    k4.metric("🔄 Returning Patients", f"{ret_pct:.1f}%",     f"Cancelled: {cancel_rate:.1f}%")

    st.divider()
    c1,c2 = st.columns(2)
    with c1:
        st.subheader("📈 Monthly Appointment Trend")
        monthly = (df.groupby(['month','month_name']).size()
                     .reset_index(name='Appointments').sort_values('month'))
        st.line_chart(monthly.set_index('month_name')['Appointments'])
    with c2:
        st.subheader("📅 Appointments by Day of Week")
        day_order  = ['Monday','Tuesday','Wednesday','Thursday','Friday','Saturday','Sunday']
        day_counts = df['day'].value_counts().reindex(day_order).dropna()
        st.bar_chart(day_counts)

    c1,c2 = st.columns(2)
    with c1:
        st.subheader("🏙️ Revenue by City")
        st.bar_chart(df.groupby('city')['fee'].sum().sort_values(ascending=False))
    with c2:
        st.subheader("🏥 Appointments by Department")
        st.bar_chart(df['department'].value_counts())

    st.subheader("⏰ No-show Rate by Appointment Hour (%)")
    hourly = (df.groupby('hour')
                .apply(lambda x: (x['status']=='No-show').mean()*100)
                .reset_index(name='No-show %'))
    st.line_chart(hourly.set_index('hour')['No-show %'])

    worst_hour = int(hourly.loc[hourly['No-show %'].idxmax(),'hour'])
    st.markdown(f"""<div class='insight-box'>
    💡 <b>Insight:</b> Appointments at <b>{worst_hour}:00</b> have the highest no-show rate.
    Consider sending extra reminders 24h before slots in this hour.</div>""", unsafe_allow_html=True)

    st.subheader("📊 Appointment Status Breakdown")
    st.bar_chart(df['status'].value_counts())


# ============================================================
# PAGE 2 — DEPARTMENT ANALYSIS
# ============================================================
elif page == "🏥 Department Analysis":
    st.title("🏥 Department Performance Analysis")

    dept = df.groupby('department').agg(
        Appointments    = ('patient_id','count'),
        Revenue         = ('fee','sum'),
        Avg_Fee         = ('fee','mean'),
        No_Show_Rate    = ('status', lambda x: (x=='No-show').mean()*100),
        Completion_Rate = ('status', lambda x: (x=='Completed').mean()*100),
        Cancel_Rate     = ('status', lambda x: (x=='Cancelled').mean()*100),
    ).reset_index()
    dept['Revenue_Share_%'] = (dept['Revenue'] / dept['Revenue'].sum()*100).round(1)
    lost_by_dept = df[df['status']=='No-show'].groupby('department')['fee'].sum()
    dept['Lost_Revenue'] = dept['department'].map(lost_by_dept).fillna(0)
    dept['Status'] = dept['No_Show_Rate'].apply(
        lambda x: '🔴 Underperforming' if x>25 else ('🟡 Average' if x>15 else '🟢 Good'))
    dept = dept.sort_values('No_Show_Rate', ascending=False).reset_index(drop=True)

    st.subheader("📊 Department Summary")
    st.dataframe(
        dept.style
            .format({'Revenue':'Rs {:,.0f}','Avg_Fee':'Rs {:,.0f}','Lost_Revenue':'Rs {:,.0f}',
                     'No_Show_Rate':'{:.1f}%','Completion_Rate':'{:.1f}%',
                     'Cancel_Rate':'{:.1f}%','Revenue_Share_%':'{:.1f}%'})
            .background_gradient(subset=['No_Show_Rate'], cmap='RdYlGn_r')
            .background_gradient(subset=['Lost_Revenue'], cmap='Reds'),
        use_container_width=True,
    )

    c1,c2 = st.columns(2)
    with c1:
        st.subheader("📉 No-show Rate by Department")
        st.bar_chart(dept.set_index('department')['No_Show_Rate'])
    with c2:
        st.subheader("💰 Revenue vs Lost Revenue")
        st.bar_chart(dept.set_index('department')[['Revenue','Lost_Revenue']])

    st.divider()
    bad = dept[dept['Status']=='🔴 Underperforming']
    if not bad.empty:
        st.error(f"⚠️ {len(bad)} department(s) underperforming (No-show > 25%)")
        for _,r in bad.iterrows():
            st.warning(f"**{r['department']}** — No-show: **{r['No_Show_Rate']:.1f}%** | "
                       f"Revenue: Rs {r['Revenue']:,.0f} | Lost: Rs {r['Lost_Revenue']:,.0f}")
    else:
        st.success("✅ All departments within acceptable thresholds.")


# ============================================================
# PAGE 3 — DOCTOR PERFORMANCE
# ============================================================
elif page == "👨‍⚕️ Doctor Performance":
    st.title("👨‍⚕️ Doctor Performance Analysis")

    doc = df.groupby(['doctor','specialization']).agg(
        Appointments    = ('patient_id','count'),
        Revenue         = ('fee','sum'),
        Avg_Fee         = ('fee','mean'),
        No_Show_Rate    = ('status', lambda x: (x=='No-show').mean()*100),
        Completion_Rate = ('status', lambda x: (x=='Completed').mean()*100),
    ).reset_index()
    lost_by_doc = df[df['status']=='No-show'].groupby('doctor')['fee'].sum()
    doc['Lost_Revenue'] = doc['doctor'].map(lost_by_doc).fillna(0)
    doc['Performance']  = doc['No_Show_Rate'].apply(
        lambda x: '🔴 High Risk' if x>25 else ('🟡 Moderate' if x>15 else '🟢 Excellent'))
    doc = doc.sort_values('No_Show_Rate', ascending=False).reset_index(drop=True)

    st.subheader("📊 Doctor Performance Table")
    st.dataframe(
        doc.style
           .format({'Revenue':'Rs {:,.0f}','Avg_Fee':'Rs {:,.0f}','Lost_Revenue':'Rs {:,.0f}',
                    'No_Show_Rate':'{:.1f}%','Completion_Rate':'{:.1f}%'})
           .background_gradient(subset=['No_Show_Rate'], cmap='RdYlGn_r'),
        use_container_width=True,
    )

    c1,c2 = st.columns(2)
    with c1:
        st.subheader("⚠️ No-show Rate by Doctor")
        st.bar_chart(doc.set_index('doctor')['No_Show_Rate'])
    with c2:
        st.subheader("💰 Revenue by Doctor")
        st.bar_chart(doc.set_index('doctor')['Revenue'])

    st.subheader("🔄 New vs Returning Patients per Doctor")
    ret_breakdown = (df.groupby(['doctor','returning']).size().unstack(fill_value=0)
                       .rename(columns={0:'New Patients',1:'Returning Patients'}))
    st.bar_chart(ret_breakdown)


# ============================================================
# PAGE 4 — CITY REVENUE
# ============================================================
elif page == "🗺️ City Revenue":
    st.title("🗺️ City Revenue Analysis")

    city = df.groupby('city').agg(
        Revenue        = ('fee','sum'),
        Appointments   = ('patient_id','count'),
        Avg_Fee        = ('fee','mean'),
        No_Show_Rate   = ('status', lambda x: (x=='No-show').mean()*100),
        Returning_Rate = ('returning','mean'),
    ).reset_index()
    city['Rev_Per_Appt'] = city['Revenue'] / city['Appointments']
    city = city.sort_values('Revenue', ascending=False).reset_index(drop=True)

    st.subheader("📊 City Performance Table")
    st.dataframe(
        city.style
            .format({'Revenue':'Rs {:,.0f}','Avg_Fee':'Rs {:,.0f}','No_Show_Rate':'{:.1f}%',
                     'Returning_Rate':'{:.1%}','Rev_Per_Appt':'Rs {:,.0f}'})
            .background_gradient(subset=['Revenue'], cmap='Blues'),
        use_container_width=True,
    )

    c1,c2 = st.columns(2)
    with c1:
        st.subheader("💰 Revenue by City")
        st.bar_chart(city.set_index('city')['Revenue'])
    with c2:
        st.subheader("📅 Appointments by City")
        st.bar_chart(city.set_index('city')['Appointments'])

    st.subheader("🔥 Revenue Heatmap — City × Department")
    pivot = df.pivot_table(values='fee', index='city', columns='department',
                           aggfunc='sum', fill_value=0)
    st.dataframe(pivot.style.background_gradient(cmap='Blues').format('Rs {:,.0f}'),
                 use_container_width=True)

    st.subheader("📈 Monthly Revenue Trend by City")
    city_month  = df.groupby(['month_name','month','city'])['fee'].sum().reset_index()
    city_month  = city_month.sort_values('month')
    pivot_trend = city_month.pivot(index='month_name', columns='city', values='fee').fillna(0)
    st.line_chart(pivot_trend)


# ============================================================
# PAGE 5 — PATIENT PROFILE  ★ NEW
# ============================================================
elif page == "👤 Patient Profile":
    st.title("👤 Patient Profile Search")
    st.caption("Search any patient to view their full appointment history, risk assessment, and lifetime value.")

    search_q = st.text_input("🔍 Search by patient name or ID", placeholder="e.g. Ali Khan or 42")

    if search_q.strip():
        mask = (
            df['patient_name'].str.contains(search_q.strip(), case=False, na=False) |
            df['patient_id'].astype(str).str.contains(search_q.strip(), na=False)
        )
        results = df[mask]
        if results.empty:
            st.warning("No patient found matching your search.")
        else:
            unique_patients = results['patient_name'].unique().tolist()
            selected_name = st.selectbox("Select patient:", unique_patients)
            patient_df = df[df['patient_name'] == selected_name].sort_values('appointment_date')
            first = patient_df.iloc[0]

            # ── Profile card ─────────────────────────────────
            st.markdown(f"""
            <div class='profile-card'>
              <div style='display:flex;align-items:center;gap:18px;'>
                <div style='width:64px;height:64px;border-radius:50%;background:#1a73e8;
                     display:flex;align-items:center;justify-content:center;
                     font-size:1.6rem;font-weight:800;color:white;'>
                  {selected_name[0]}
                </div>
                <div>
                  <div style='font-size:1.25rem;font-weight:700;color:#1a2332;'>{selected_name}</div>
                  <div style='font-size:.85rem;color:#555;'>
                    📱 {first.get('phone','—')} &nbsp;|&nbsp;
                    📧 {first.get('email','—')} &nbsp;|&nbsp;
                    🏙️ {first['city']}
                  </div>
                  <div style='font-size:.82rem;color:#888;margin-top:4px;'>
                    Patient ID: #{first['patient_id']} &nbsp;|&nbsp;
                    Type: {'🔄 Returning' if first['returning'] else '🆕 New'}
                  </div>
                </div>
              </div>
            </div>""", unsafe_allow_html=True)

            # ── KPI metrics ──────────────────────────────────
            m1,m2,m3,m4,m5 = st.columns(5)
            m1.metric("📅 Total Appointments",  len(patient_df))
            m2.metric("💰 Total Spent",          f"Rs {patient_df['fee'].sum():,}")
            m3.metric("✅ Completion Rate",       f"{(patient_df['status']=='Completed').mean()*100:.0f}%")
            m4.metric("⚠️ No-show Rate",          f"{(patient_df['status']=='No-show').mean()*100:.0f}%")
            m5.metric("🏥 Dept Visited",          patient_df['department'].nunique())

            # ── Risk assessment ───────────────────────────────
            st.divider()
            st.subheader("🧠 AI Risk Assessment")
            latest = patient_df.iloc[-1]
            X_p = [[
                le_city.transform([latest['city']])[0],
                le_dept.transform([latest['department']])[0],
                le_doctor.transform([latest['doctor']])[0],
                int(latest['returning']), int(latest['hour']),
                int(latest['day_of_week']), int(latest['month']),
            ]]
            risk_prob = model.predict_proba(X_p)[0][1] * 100
            risk_level = "🔴 HIGH" if risk_prob >= 60 else ("🟡 MEDIUM" if risk_prob >= 35 else "🟢 LOW")

            rc1, rc2 = st.columns([1,2])
            rc1.metric("Current Risk Score", f"{risk_prob:.1f}%")
            rc1.metric("Risk Level", risk_level)
            with rc2:
                fig_gauge = go.Figure(go.Indicator(
                    mode="gauge+number",
                    value=risk_prob,
                    number={'suffix':'%','font':{'size':28}},
                    gauge={
                        'axis':{'range':[0,100]},
                        'bar':{'color':'#1a73e8'},
                        'steps':[
                            {'range':[0,35],'color':'#c8e6c9'},
                            {'range':[35,60],'color':'#fff9c4'},
                            {'range':[60,100],'color':'#ffcdd2'},
                        ],
                        'threshold':{'line':{'color':'red','width':3},'thickness':.75,'value':60}
                    },
                    title={'text':"No-show Risk"},
                ))
                fig_gauge.update_layout(height=200, margin=dict(t=30,b=0,l=20,r=20))
                st.plotly_chart(fig_gauge, use_container_width=True)

            # ── Appointment history table ─────────────────────
            st.divider()
            st.subheader("📋 Appointment History")
            history = patient_df[[
                'appointment_date','department','doctor','status','fee','hour'
            ]].copy()
            history['appointment_date'] = history['appointment_date'].dt.strftime('%Y-%m-%d')
            history = history.sort_values('appointment_date', ascending=False)

            def color_status(val):
                if val == 'No-show': return 'color:red;font-weight:600'
                if val == 'Completed': return 'color:green;font-weight:600'
                return 'color:orange;font-weight:600'

            st.dataframe(
                history.style.applymap(color_status, subset=['status'])
                             .format({'fee':'Rs {:,.0f}'}),
                use_container_width=True
            )

            # ── Reminder history ──────────────────────────────
            log = load_reminder_log()
            if not log.empty:
                p_log = log[log['patient_id'].astype(str)==str(first['patient_id'])]
                if not p_log.empty:
                    st.divider()
                    st.subheader("📨 Reminder History for This Patient")
                    st.dataframe(p_log[['sent_at','channel','risk_level','message_type']],
                                 use_container_width=True)
                else:
                    st.info("ℹ️ No reminders have been sent to this patient yet.")
    else:
        st.info("👆 Start typing a patient name or ID above to search.")

        # ── Quick stats ──────────────────────────────────────
        st.divider()
        st.subheader("📊 Patient Database Overview")
        c1,c2,c3 = st.columns(3)
        c1.metric("Total Unique Patients", df['patient_name'].nunique())
        c2.metric("New Patients",          (df[df['returning']==0]['patient_name'].nunique()))
        c3.metric("Returning Patients",    (df[df['returning']==1]['patient_name'].nunique()))

        top5 = (df.groupby('patient_name')['fee'].sum()
                  .sort_values(ascending=False).head(5).reset_index())
        top5.columns = ['Patient','Total Spent']
        top5['Total Spent'] = top5['Total Spent'].apply(lambda x: f"Rs {x:,}")
        st.subheader("🏆 Top 5 Patients by Total Spend")
        st.dataframe(top5, use_container_width=True)


# ============================================================
# PAGE 6 — BOOK APPOINTMENT  ★ NEW
# ============================================================
elif page == "📅 Book Appointment":
    st.title("📅 Book New Appointment")
    st.caption("Register a new patient appointment directly into the system.")

    with st.form("booking_form", clear_on_submit=True):
        st.markdown("### 👤 Patient Information")
        bc1, bc2 = st.columns(2)
        p_name   = bc1.text_input("Patient Name *", placeholder="e.g. Ali Khan")
        p_phone  = bc2.text_input("Phone *",         placeholder="e.g. 03001234567")
        p_email  = bc1.text_input("Email",            placeholder="e.g. ali@gmail.com")
        p_city   = bc2.selectbox("City *", CITIES)

        st.markdown("### 🏥 Appointment Details")
        ad1, ad2, ad3 = st.columns(3)
        p_dept   = ad1.selectbox("Department *", DEPARTMENTS)
        p_doctor = ad2.selectbox("Doctor *", list(DOCTOR_MAP.keys()))
        p_date   = ad3.date_input("Date *", min_value=datetime.today(),
                                  value=datetime.today() + timedelta(days=1))

        ah1, ah2 = st.columns(2)
        p_hour   = ah1.slider("Appointment Hour", 9, 18, 10,
                               format_func=lambda x: f"{x}:00 {'AM' if x<12 else 'PM'}")
        p_type   = ah2.selectbox("Patient Type", [0,1],
                                  format_func=lambda x: "🆕 New Patient" if x==0 else "🔄 Returning Patient")

        st.markdown("### 💰 Fee")
        p_fee = st.number_input("Consultation Fee (Rs)", min_value=500, max_value=10000,
                                value=2000, step=500)

        submitted = st.form_submit_button("✅ Confirm Appointment", type="primary", use_container_width=True)

        if submitted:
            if not p_name.strip() or not p_phone.strip():
                st.error("❌ Patient Name and Phone are required.")
            else:
                new_id  = int(df['patient_id'].max()) + 1
                new_row = {
                    'patient_id':       new_id,
                    'patient_name':     p_name.strip(),
                    'email':            p_email.strip(),
                    'phone':            p_phone.strip(),
                    'city':             p_city,
                    'department':       p_dept,
                    'doctor':           p_doctor,
                    'specialization':   DOCTOR_MAP[p_doctor],
                    'appointment_date': str(p_date),
                    'status':           'Completed',
                    'fee':              p_fee,
                    'returning':        p_type,
                    'hour':             p_hour,
                }
                new_df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
                new_df.to_csv(BOOKINGS_FILE, index=False)
                st.success(f"✅ Appointment booked for **{p_name}** on **{p_date}** at **{p_hour}:00** with **{p_doctor}**!")
                st.balloons()
                st.cache_data.clear()

    # ── Today's bookings ─────────────────────────────────────
    st.divider()
    st.subheader("📋 Recent Appointments (Last 7 Days)")
    recent = df[df['appointment_date'] >= pd.Timestamp.now() - pd.Timedelta(days=7)]
    if recent.empty:
        future = df.tail(10)
        st.dataframe(future[['patient_name','city','department','doctor',
                              'appointment_date','hour','status','fee']]
                     .sort_values('appointment_date', ascending=False),
                     use_container_width=True)
    else:
        st.dataframe(recent[['patient_name','city','department','doctor',
                              'appointment_date','hour','status','fee']]
                     .sort_values('appointment_date', ascending=False),
                     use_container_width=True)

    # ── Slot availability heatmap ─────────────────────────────
    st.divider()
    st.subheader("⏰ Appointment Slot Demand (Hour vs Day)")
    slot_pivot = df.groupby(['day_of_week','hour']).size().unstack(fill_value=0)
    slot_pivot.index = ['Mon','Tue','Wed','Thu','Fri','Sat','Sun'][:len(slot_pivot)]
    fig_slot = px.imshow(
        slot_pivot, color_continuous_scale='Blues',
        labels=dict(x="Hour", y="Day", color="Bookings"),
        title="Busy slots — darker = more bookings",
    )
    fig_slot.update_layout(height=280, margin=dict(t=40,b=20,l=20,r=20))
    st.plotly_chart(fig_slot, use_container_width=True)


# ============================================================
# PAGE 7 — SMART REMINDERS
# ============================================================
elif page == "🧠 Smart Reminders":
    st.title("🧠 Smart Reminder Engine")
    st.caption("AI-powered, risk-stratified reminders — right message, right patient, right channel, right time.")

    df_risk = df.copy()
    df_risk['city_enc']   = le_city.transform(df_risk['city'])
    df_risk['dept_enc']   = le_dept.transform(df_risk['department'])
    df_risk['doctor_enc'] = le_doctor.transform(df_risk['doctor'])
    X_all = df_risk[['city_enc','dept_enc','doctor_enc','returning','hour','day_of_week','month']]
    df_risk['risk_score'] = (model.predict_proba(X_all)[:,1]*100).round(1)

    log          = load_reminder_log()
    reminded_ids = set(log['patient_id'].astype(str).tolist()) if not log.empty else set()

    st.markdown("<div class='section-header'>🎯 Filter & Segment Patients</div>", unsafe_allow_html=True)
    c1,c2,c3,c4,c5 = st.columns(5)
    with c1: threshold = st.slider("Min Risk Score (%)", 10, 80, 35)
    with c2: city_f   = st.multiselect("City", df['city'].unique(), default=list(df['city'].unique()))
    with c3: dept_f   = st.multiselect("Department", df['department'].unique(), default=list(df['department'].unique()))
    with c4: doctor_f = st.multiselect("Doctor", df['doctor'].unique(), default=list(df['doctor'].unique()))
    with c5: pt_type  = st.selectbox("Patient Type", ["All","New Only","Returning Only"])

    mask = ((df_risk['risk_score']>=threshold) & df_risk['city'].isin(city_f) &
            df_risk['department'].isin(dept_f) & df_risk['doctor'].isin(doctor_f))
    if pt_type=="New Only":      mask &= (df_risk['returning']==0)
    elif pt_type=="Returning Only": mask &= (df_risk['returning']==1)

    at_risk = df_risk[mask].copy()
    at_risk['Reminded']     = at_risk['patient_id'].astype(str).isin(reminded_ids)
    at_risk['Patient Type'] = at_risk['returning'].map({0:'🆕 New',1:'🔄 Returning'})
    at_risk['Risk Level']   = at_risk['risk_score'].apply(
        lambda x: '🔴 High' if x>=60 else ('🟡 Medium' if x>=35 else '🟢 Low'))

    st.divider()
    m1,m2,m3,m4,m5 = st.columns(5)
    m1.metric("🔍 Total At-Risk",    len(at_risk))
    m2.metric("🔴 High Risk",        len(at_risk[at_risk['Risk Level']=='🔴 High']))
    m3.metric("🟡 Medium Risk",      len(at_risk[at_risk['Risk Level']=='🟡 Medium']))
    m4.metric("✅ Already Reminded", at_risk['Reminded'].sum())
    m5.metric("📨 Pending",          (~at_risk['Reminded']).sum())

    high_risk   = at_risk[at_risk['Risk Level']=='🔴 High']
    medium_risk = at_risk[at_risk['Risk Level']=='🟡 Medium']
    low_risk    = at_risk[at_risk['Risk Level']=='🟢 Low']

    st.divider()
    st.markdown("<div class='section-header'>📡 Smart Channel Recommendation</div>", unsafe_allow_html=True)
    ra,rb,rc = st.columns(3)
    with ra:
        st.markdown(f"<div class='reminder-card'><b style='color:#ff4757;'>🔴 High Risk — {len(high_risk)} patients</b><br>"
                    f"<small>Channel: <b>📱 SMS + 📞 Call</b></small><br>"
                    f"<small>Timing: <b>48h AND 24h</b> before</small><br>"
                    f"<small>Tone: Urgent & personalised</small></div>", unsafe_allow_html=True)
    with rb:
        st.markdown(f"<div class='reminder-card'><b style='color:#ffa502;'>🟡 Medium — {len(medium_risk)} patients</b><br>"
                    f"<small>Channel: <b>📧 Email + 📱 SMS</b></small><br>"
                    f"<small>Timing: <b>24h</b> before</small><br>"
                    f"<small>Tone: Friendly reminder</small></div>", unsafe_allow_html=True)
    with rc:
        st.markdown(f"<div class='reminder-card'><b style='color:#2ed573;'>🟢 Low — {len(low_risk)} patients</b><br>"
                    f"<small>Channel: <b>📧 Email only</b></small><br>"
                    f"<small>Timing: <b>24h</b> before</small><br>"
                    f"<small>Tone: Simple confirmation</small></div>", unsafe_allow_html=True)

    st.divider()
    st.markdown("<div class='section-header'>✍️ Smart Message Preview</div>", unsafe_allow_html=True)
    pending = at_risk[~at_risk['Reminded']].copy()

    if not pending.empty:
        preview_name = st.selectbox("Preview message for:", pending['patient_name'].head(20).tolist())
        sel = pending[pending['patient_name']==preview_name].iloc[0]
        auto_msg = generate_smart_message(sel['patient_name'], sel['doctor'], sel['department'],
                                          sel['risk_score'], sel['appointment_date'],
                                          sel['hour'], sel['returning'], sel['city'])
        st.text_area("📝 Edit before sending:", value=auto_msg, height=170)

        st.divider()
        sc1,sc2,sc3 = st.columns(3)
        with sc1:
            channel = st.radio("📡 Channel", ["📱 SMS (Simulated)","📧 Email (Simulated)",
                                              "📱📧 Both (Simulated)","📞 Call (Simulated)"])
        with sc2:
            send_seg = st.radio("👥 Send To", [
                f"🔴 High Risk Only ({len(high_risk[~high_risk['Reminded']])} pending)",
                f"🟡 Medium + High ({len(pending[pending['Risk Level'].isin(['🔴 High','🟡 Medium'])])} pending)",
                f"📋 All Pending ({len(pending)} pending)",
            ])
        with sc3:
            st.markdown("<br>", unsafe_allow_html=True)
            send_btn = st.button("🚀 Send Smart Reminders", type="primary", use_container_width=True)
            dry_run  = st.checkbox("🧪 Dry Run (preview only)")

        if send_btn:
            if "High Risk Only" in send_seg:
                to_send  = high_risk[~high_risk['Reminded']]; msg_type="High-Risk Urgent"
            elif "Medium + High" in send_seg:
                to_send  = pending[pending['Risk Level'].isin(['🔴 High','🟡 Medium'])]; msg_type="Medium-High"
            else:
                to_send  = pending; msg_type="Standard"

            if dry_run:
                st.info(f"🧪 **Dry Run:** Would send {len(to_send)} reminders. Nothing saved.")
                st.dataframe(to_send[['patient_name','Risk Level','risk_score','doctor','department']].head(10))
            else:
                with st.spinner(f"Dispatching {len(to_send)} smart reminders…"):
                    bar = st.progress(0)
                    for i,(_, row) in enumerate(to_send.iterrows()):
                        time.sleep(0.005)
                        bar.progress((i+1)/max(len(to_send),1))
                    save_reminders(to_send, channel, msg_type)
                st.success(f"✅ {len(to_send)} **{msg_type}** reminders sent via **{channel}**!")
                st.balloons()
                st.cache_data.clear()
    else:
        st.info("✅ All at-risk patients in this filter have already been reminded.")

    st.divider()
    st.subheader("📋 At-Risk Patient Table")
    display = at_risk[['patient_id','patient_name','phone','city','department','doctor',
                        'appointment_date','hour','Patient Type','risk_score','Risk Level','Reminded']].copy()
    display = display.rename(columns={'patient_id':'ID','patient_name':'Patient','appointment_date':'Date',
                                       'risk_score':'Risk %','Reminded':'Reminded ✅'})
    display['Date'] = display['Date'].dt.strftime('%Y-%m-%d')
    st.dataframe(display.style.background_gradient(subset=['Risk %'], cmap='RdYlGn_r')
                              .format({'Risk %':'{:.1f}%'}),
                 use_container_width=True, height=380)
    st.download_button("⬇️ Download At-Risk List", display.to_csv(index=False).encode(),
                       "at_risk_patients.csv","text/csv")


# ============================================================
# PAGE 8 — REMINDER ANALYTICS
# ============================================================
elif page == "📈 Reminder Analytics":
    st.title("📈 Reminder Analytics & Effectiveness")
    log = load_reminder_log()

    if log.empty:
        st.warning("No reminders sent yet. Head to the Smart Reminders page to get started.")
    else:
        log['sent_at'] = pd.to_datetime(log['sent_at'])
        log['date']    = log['sent_at'].dt.date

        m1,m2,m3,m4 = st.columns(4)
        m1.metric("📨 Total Sent",          len(log))
        m2.metric("👥 Unique Patients",      log['patient_id'].nunique())
        m3.metric("📡 Channels Used",        log['channel'].nunique())
        m4.metric("🏥 Depts Covered",        log['department'].nunique() if 'department' in log.columns else "—")

        st.divider()
        c1,c2 = st.columns(2)
        with c1:
            st.subheader("📡 Reminders by Channel")
            st.bar_chart(log['channel'].value_counts())
        with c2:
            st.subheader("📅 Reminders Sent Per Day")
            daily = log.groupby('date').size().reset_index(name='Count')
            st.line_chart(daily.set_index('date')['Count'])

        if 'risk_level' in log.columns and log['risk_level'].notna().any():
            c1,c2 = st.columns(2)
            with c1:
                st.subheader("🎯 Reminders by Risk Level")
                st.bar_chart(log['risk_level'].value_counts())
            with c2:
                if 'department' in log.columns:
                    st.subheader("🏥 Reminders by Department")
                    st.bar_chart(log['department'].value_counts())

        st.subheader("📋 Full Reminder Log")
        st.dataframe(log.sort_values('sent_at', ascending=False), use_container_width=True, height=340)
        st.download_button("⬇️ Download Log", log.to_csv(index=False).encode(),
                           "reminder_log.csv","text/csv")


# ============================================================
# PAGE 9 — NO-SHOW PREDICTOR + SHAP  ★ ENHANCED
# ============================================================
elif page == "🔮 No-Show Predictor":
    st.title("🔮 No-Show Risk Predictor")
    st.caption("AI-powered prediction with full SHAP explainability — understand *why* the model thinks a patient will no-show.")

    c1,c2 = st.columns(2)
    with c1:
        patient_name  = st.text_input("👤 Patient Name",  placeholder="e.g. Ali Khan")
        patient_phone = st.text_input("📱 Phone",          placeholder="e.g. 03001234567")
        city_sel      = st.selectbox("🏙️ City",            le_city.classes_)
        dept_sel      = st.selectbox("🏥 Department",      le_dept.classes_)
        doctor_sel    = st.selectbox("👨‍⚕️ Doctor",          le_doctor.classes_)
    with c2:
        returning_sel = st.selectbox("Patient Type", [0,1],
                                     format_func=lambda x: "🆕 New Patient" if x==0 else "🔄 Returning Patient")
        hour_sel  = st.slider("⏰ Appointment Hour", 9, 18, 10)
        dow_sel   = st.selectbox("📅 Day of Week", list(range(7)),
                                 format_func=lambda x: ['Monday','Tuesday','Wednesday',
                                                         'Thursday','Friday','Saturday','Sunday'][x])
        month_sel = st.selectbox("🗓️ Month", list(range(1,13)),
                                 format_func=lambda x: ['Jan','Feb','Mar','Apr','May','Jun',
                                                          'Jul','Aug','Sep','Oct','Nov','Dec'][x-1])

    if st.button("🔮 Predict No-Show Risk", type="primary"):
        X_pred = [[
            le_city.transform([city_sel])[0],
            le_dept.transform([dept_sel])[0],
            le_doctor.transform([doctor_sel])[0],
            returning_sel, hour_sel, dow_sel, month_sel,
        ]]

        prob  = model.predict_proba(X_pred)[0][1]*100
        pred  = model.predict(X_pred)[0]
        level = "🔴 HIGH" if prob>=60 else ("🟡 MEDIUM" if prob>=35 else "🟢 LOW")

        st.divider()
        r1,r2,r3,r4 = st.columns(4)
        r1.metric("Patient",             patient_name or "—")
        r2.metric("No-show Probability", f"{prob:.1f}%")
        r3.metric("Risk Level",          level)
        r4.metric("Phone",               patient_phone or "—")
        st.progress(int(min(prob,100)))

        if pred==1:
            st.error(f"⚠️ **HIGH NO-SHOW RISK** ({prob:.1f}%) — Immediate action required.")
        else:
            st.success(f"✅ **LOW RISK** ({prob:.1f}%) — Patient likely to attend.")

        # ── SHAP Explainability ──────────────────────────────
        st.divider()
        st.subheader("🧠 Why This Prediction? — SHAP Explainability")

        if SHAP_OK and shap_explainer is not None:
            shap_vals = shap_explainer.shap_values(np.array(X_pred))
            # shap_values returns list [class0, class1] for classifier
            sv = shap_vals[1][0] if isinstance(shap_vals, list) else shap_vals[0]

            shap_df = pd.DataFrame({
                'Feature': FEATURE_NAMES,
                'SHAP Value': sv,
                'Actual Value': [city_sel, dept_sel, doctor_sel,
                                 'Returning' if returning_sel else 'New',
                                 f"{hour_sel}:00", ['Mon','Tue','Wed','Thu','Fri','Sat','Sun'][dow_sel],
                                 ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'][month_sel-1]]
            }).sort_values('SHAP Value', key=abs, ascending=True)

            colors = ['#ff4757' if v>0 else '#2ed573' for v in shap_df['SHAP Value']]
            fig_shap = go.Figure(go.Bar(
                x=shap_df['SHAP Value'], y=shap_df['Feature'],
                orientation='h', marker_color=colors,
                text=[f"{v:+.3f} ({av})" for v,av in zip(shap_df['SHAP Value'], shap_df['Actual Value'])],
                textposition='outside',
            ))
            fig_shap.update_layout(
                title="Feature contributions to no-show risk (red = increases risk, green = decreases risk)",
                xaxis_title="SHAP Value (impact on prediction)",
                height=340, margin=dict(t=50,b=20,l=20,r=120),
                plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)',
            )
            st.plotly_chart(fig_shap, use_container_width=True)

            # Top driver
            top_feature = shap_df.iloc[-1]
            direction   = "increases" if top_feature['SHAP Value']>0 else "decreases"
            st.markdown(f"""<div class='insight-box'>
            🧠 <b>Top Driver:</b> <b>{top_feature['Feature']}</b> ({top_feature['Actual Value']})
            {direction} no-show risk the most for this patient.</div>""", unsafe_allow_html=True)
        else:
            st.info("💡 Install the `shap` library to enable AI explainability: `pip install shap`")

        # ── Action recommendations ────────────────────────────
        st.divider()
        st.subheader("💡 Action Recommendations")
        if prob>=60:
            st.warning("📱 Send **urgent SMS** 48h AND 24h before the appointment.")
            st.warning("📞 Schedule a **phone call** on appointment morning.")
            st.warning("📋 Consider **double-booking** this slot as a buffer.")
        elif prob>=35:
            st.info("📧 Send a **standard email reminder** with appointment details.")
            st.info("📱 Follow up with an **SMS** 24h before.")
        else:
            st.success("📩 Standard automated reminder is sufficient.")
            st.success("✅ No additional action needed.")

        # ── Auto message ──────────────────────────────────────
        st.divider()
        st.subheader("✍️ Auto-Generated Reminder Message")
        smart_msg = generate_smart_message(patient_name or "Patient", doctor_sel, dept_sel,
                                           prob, None, hour_sel, returning_sel, city_sel)
        st.text_area("Message Preview", value=smart_msg, height=160)


# ============================================================
# PAGE 10 — REVENUE FORECAST  ★ NEW
# ============================================================
elif page == "📉 Revenue Forecast":
    st.title("📉 Revenue Forecast")
    st.caption("AI-powered trend projection for next 30, 60, and 90 days based on historical patterns.")

    horizon = st.radio("Forecast Horizon", ["30 Days","60 Days","90 Days"], horizontal=True)
    h_days  = int(horizon.split()[0])

    # ── Build daily revenue series ────────────────────────────
    daily = (df[df['status']=='Completed']
             .groupby('appointment_date')['fee'].sum()
             .reset_index().sort_values('appointment_date'))
    daily.columns = ['date','revenue']

    x  = np.arange(len(daily))
    y  = daily['revenue'].values

    # Polynomial trend fit (degree 2)
    coeffs    = np.polyfit(x, y, deg=2)
    trend     = np.polyval(coeffs, x)
    residuals = y - trend
    std_resid = residuals.std()

    # Forecast
    x_future     = np.arange(len(x), len(x) + h_days)
    future_trend = np.polyval(coeffs, x_future)
    last_date    = daily['date'].max()
    future_dates = [last_date + timedelta(days=i+1) for i in range(h_days)]

    # ── Forecast KPIs ─────────────────────────────────────────
    proj_total   = future_trend.sum()
    proj_daily   = future_trend.mean()
    proj_peak    = future_trend.max()
    hist_daily   = y.mean()
    change_pct   = (proj_daily - hist_daily) / hist_daily * 100

    m1,m2,m3,m4 = st.columns(4)
    m1.metric(f"💰 Projected Revenue ({h_days}d)", f"Rs {proj_total:,.0f}")
    m2.metric("📅 Projected Daily Avg",             f"Rs {proj_daily:,.0f}", f"{change_pct:+.1f}% vs history")
    m3.metric("📈 Peak Day Forecast",               f"Rs {proj_peak:,.0f}")
    m4.metric("📊 Historical Daily Avg",            f"Rs {hist_daily:,.0f}")

    st.divider()

    # ── Main forecast chart ───────────────────────────────────
    fig = go.Figure()

    # Historical actual
    fig.add_trace(go.Scatter(
        x=daily['date'], y=y, name='Historical Revenue',
        line=dict(color='#1a73e8', width=1.5), opacity=0.7
    ))
    # Historical trend
    fig.add_trace(go.Scatter(
        x=daily['date'], y=trend, name='Trend Line',
        line=dict(color='#f5a623', width=2, dash='dot')
    ))
    # Forecast upper CI
    upper = future_trend + 1.96 * std_resid
    lower = np.clip(future_trend - 1.96 * std_resid, 0, None)
    fig.add_trace(go.Scatter(
        x=future_dates + future_dates[::-1],
        y=list(upper) + list(lower[::-1]),
        fill='toself', fillcolor='rgba(0,184,148,0.15)',
        line=dict(color='rgba(0,0,0,0)'), name='95% Confidence Band', showlegend=True
    ))
    # Forecast line
    fig.add_trace(go.Scatter(
        x=future_dates, y=future_trend, name=f'{h_days}-Day Forecast',
        line=dict(color='#00b894', width=2.5)
    ))
    # Divider line
    fig.add_vline(x=str(last_date), line_dash="dash", line_color="gray",
                  annotation_text="Forecast Start", annotation_position="top left")

    fig.update_layout(
        title=f"Revenue Forecast — Next {h_days} Days",
        xaxis_title="Date", yaxis_title="Revenue (Rs)",
        height=430, hovermode='x unified',
        plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)',
        legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='left', x=0),
    )
    fig.update_xaxes(showgrid=True, gridcolor='rgba(0,0,0,0.05)')
    fig.update_yaxes(showgrid=True, gridcolor='rgba(0,0,0,0.05)')
    st.plotly_chart(fig, use_container_width=True)

    # ── Monthly appointment trend forecast ───────────────────
    st.subheader("📊 Monthly Appointment Volume — Historical + Forecast")
    monthly_appts = df.groupby('month').size().reset_index(name='Appointments')
    xm = monthly_appts['month'].values
    ym = monthly_appts['Appointments'].values
    cm = np.polyfit(xm, ym, deg=1)
    future_months = list(range(xm.max()+1, xm.max()+4))
    future_appts  = np.polyval(cm, future_months)

    fig2 = go.Figure()
    fig2.add_trace(go.Bar(x=monthly_appts['month'], y=ym, name='Historical', marker_color='#1a73e8'))
    fig2.add_trace(go.Bar(x=future_months, y=future_appts, name='Forecast', marker_color='#00b894', opacity=0.7))
    fig2.update_layout(barmode='group', height=300,
                       xaxis_title="Month", yaxis_title="Appointments",
                       plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)')
    st.plotly_chart(fig2, use_container_width=True)

    st.markdown(f"""<div class='insight-box'>
    📉 <b>Forecast Insight:</b> Based on current trends, the projected daily revenue over the next <b>{h_days} days</b>
    is <b>Rs {proj_daily:,.0f}</b> — a <b>{change_pct:+.1f}%</b> {'increase' if change_pct>=0 else 'decrease'} vs historical average.
    The 95% confidence band accounts for natural day-to-day variability (±Rs {1.96*std_resid:,.0f}).
    </div>""", unsafe_allow_html=True)


# ============================================================
# PAGE 11 — REVENUE INTELLIGENCE
# ============================================================
elif page == "💡 Revenue Intelligence":
    st.title("💡 Revenue Intelligence")
    st.caption("Where money is earned, where it is lost, and what to do about it.")

    total_rev  = df['fee'].sum()
    earned_rev = df[df['status']=='Completed']['fee'].sum()
    lost_rev   = df[df['status']=='No-show']['fee'].sum()
    cancel_rev = df[df['status']=='Cancelled']['fee'].sum()
    recovery   = lost_rev * 0.5

    m1,m2,m3,m4 = st.columns(4)
    m1.metric("💰 Revenue Earned",        f"Rs {earned_rev:,}",  f"{earned_rev/total_rev*100:.1f}% of total")
    m2.metric("❌ Lost to No-shows",       f"Rs {lost_rev:,}",   f"{lost_rev/total_rev*100:.1f}% of total")
    m3.metric("🚫 Lost to Cancellations", f"Rs {cancel_rev:,}", f"{cancel_rev/total_rev*100:.1f}% of total")
    m4.metric("🎯 50% Recovery Potential", f"Rs {recovery:,.0f}","with smart reminders")

    st.divider()
    c1,c2 = st.columns(2)
    with c1:
        st.subheader("💸 Revenue Lost by Doctor")
        lost_doc = df[df['status']=='No-show'].groupby('doctor')['fee'].sum().sort_values(ascending=False)
        st.bar_chart(lost_doc)
    with c2:
        st.subheader("💸 Revenue Lost by Department")
        lost_dept = df[df['status']=='No-show'].groupby('department')['fee'].sum().sort_values(ascending=False)
        st.bar_chart(lost_dept)

    st.subheader("⏰ Earned vs Lost Revenue by Hour")
    hourly_rev  = df[df['status']=='Completed'].groupby('hour')['fee'].sum()
    hourly_lost = df[df['status']=='No-show'].groupby('hour')['fee'].sum()
    st.bar_chart(pd.DataFrame({'Earned':hourly_rev,'Lost':hourly_lost}).fillna(0))

    st.subheader("📈 Monthly Earned vs Lost Revenue")
    monthly_earned = df[df['status']=='Completed'].groupby('month_name')['fee'].sum()
    monthly_lost   = df[df['status']=='No-show'].groupby('month_name')['fee'].sum()
    st.bar_chart(pd.DataFrame({'Earned':monthly_earned,'Lost to No-shows':monthly_lost}).fillna(0))

    best_dept  = df[df['status']=='Completed'].groupby('department')['fee'].sum().idxmax()
    worst_dept = df[df['status']=='No-show'].groupby('department')['fee'].sum().idxmax()
    worst_loss = df[(df['status']=='No-show')&(df['department']==worst_dept)]['fee'].sum()
    st.markdown(f"""<div class='insight-box'>
    💡 <b>Revenue Intelligence:</b> <b>{best_dept}</b> is your top-earning department.
    <b>{worst_dept}</b> causes the most revenue leakage (Rs {worst_loss:,}).
    Directing Smart Reminders at <b>{worst_dept}</b> patients could recover up to
    <b>Rs {worst_loss//2:,}</b> — a 50% improvement estimate.</div>""", unsafe_allow_html=True)


# ============================================================
# PAGE 12 — KPI GOALS  ★ NEW
# ============================================================
elif page == "🎯 KPI Goals":
    st.title("🎯 KPI Goal Tracker")
    st.caption("Set monthly targets for your clinic and track actual vs goal in real time.")

    # ── Goal configuration ─────────────────────────────────────
    with st.expander("⚙️ Configure Goals", expanded=False):
        gc1,gc2,gc3 = st.columns(3)
        with gc1:
            new_rev = st.number_input("💰 Revenue Target (Rs)", min_value=1000000,
                                      max_value=20000000, value=st.session_state.goals['revenue'],
                                      step=500000, format="%d")
        with gc2:
            new_ns = st.number_input("⚠️ Max No-show Rate (%)", min_value=1.0, max_value=50.0,
                                     value=st.session_state.goals['no_show_cap'], step=0.5)
        with gc3:
            new_appts = st.number_input("📅 Appointment Target", min_value=100, max_value=10000,
                                        value=st.session_state.goals['appointments'], step=100)
        if st.button("💾 Save Goals"):
            st.session_state.goals = {'revenue': new_rev, 'no_show_cap': new_ns, 'appointments': new_appts}
            st.success("✅ Goals updated!")

    goals = st.session_state.goals

    # ── Actual values ─────────────────────────────────────────
    actual_rev   = df[df['status']=='Completed']['fee'].sum()
    actual_ns    = (df['status']=='No-show').mean()*100
    actual_appts = len(df)

    # ── Plotly gauge subplots ─────────────────────────────────
    fig = make_subplots(rows=1, cols=3, specs=[[{'type':'indicator'}]*3],
                        subplot_titles=["Revenue Goal","No-show Rate Cap","Appointment Target"])

    # Revenue gauge
    fig.add_trace(go.Indicator(
        mode="gauge+number+delta",
        value=actual_rev,
        delta={'reference': goals['revenue'], 'relative':True, 'valueformat':'.1%'},
        number={'prefix':'Rs ','valueformat':',.0f','font':{'size':18}},
        gauge={
            'axis':{'range':[0, goals['revenue']*1.3]},
            'bar':{'color':'#1a73e8','thickness':0.3},
            'steps':[
                {'range':[0, goals['revenue']*0.5],'color':'#ffcdd2'},
                {'range':[goals['revenue']*0.5, goals['revenue']*0.8],'color':'#fff9c4'},
                {'range':[goals['revenue']*0.8, goals['revenue']*1.3],'color':'#c8e6c9'},
            ],
            'threshold':{'line':{'color':'#1a73e8','width':3},'thickness':0.75,'value':goals['revenue']}
        },
    ), row=1, col=1)

    # No-show rate gauge (lower is better)
    fig.add_trace(go.Indicator(
        mode="gauge+number+delta",
        value=actual_ns,
        delta={'reference': goals['no_show_cap'], 'relative':False, 'valueformat':'.1f',
               'decreasing':{'color':'green'},'increasing':{'color':'red'}},
        number={'suffix':'%','font':{'size':22}},
        gauge={
            'axis':{'range':[0,50]},
            'bar':{'color':'#e74c3c' if actual_ns > goals['no_show_cap'] else '#27ae60','thickness':0.3},
            'steps':[
                {'range':[0, goals['no_show_cap']],'color':'#c8e6c9'},
                {'range':[goals['no_show_cap'],30],'color':'#fff9c4'},
                {'range':[30,50],'color':'#ffcdd2'},
            ],
            'threshold':{'line':{'color':'red','width':3},'thickness':0.75,'value':goals['no_show_cap']}
        },
    ), row=1, col=2)

    # Appointment gauge
    fig.add_trace(go.Indicator(
        mode="gauge+number+delta",
        value=actual_appts,
        delta={'reference': goals['appointments'], 'relative':True, 'valueformat':'.1%'},
        number={'font':{'size':22}},
        gauge={
            'axis':{'range':[0, goals['appointments']*1.3]},
            'bar':{'color':'#00b894','thickness':0.3},
            'steps':[
                {'range':[0, goals['appointments']*0.5],'color':'#ffcdd2'},
                {'range':[goals['appointments']*0.5, goals['appointments']*0.8],'color':'#fff9c4'},
                {'range':[goals['appointments']*0.8, goals['appointments']*1.3],'color':'#c8e6c9'},
            ],
            'threshold':{'line':{'color':'#00b894','width':3},'thickness':0.75,'value':goals['appointments']}
        },
    ), row=1, col=3)

    fig.update_layout(height=380, margin=dict(t=60,b=20,l=20,r=20))
    st.plotly_chart(fig, use_container_width=True)

    # ── Progress bars ─────────────────────────────────────────
    st.subheader("📊 Goal Progress Summary")
    pc1,pc2,pc3 = st.columns(3)

    with pc1:
        rev_pct = min(actual_rev / goals['revenue'] * 100, 100)
        col = "green" if rev_pct >= 80 else ("orange" if rev_pct >= 50 else "red")
        st.metric("💰 Revenue Progress", f"{rev_pct:.1f}%",
                  f"Rs {actual_rev:,} of Rs {goals['revenue']:,}")
        st.progress(int(rev_pct))

    with pc2:
        ns_pct = actual_ns / goals['no_show_cap'] * 100
        col = "green" if ns_pct <= 100 else "red"
        st.metric("⚠️ No-show vs Cap", f"{actual_ns:.1f}% / {goals['no_show_cap']}%",
                  "✅ Within target" if actual_ns <= goals['no_show_cap'] else "❌ Exceeds target")
        st.progress(min(int(ns_pct), 100))

    with pc3:
        appt_pct = min(actual_appts / goals['appointments'] * 100, 100)
        st.metric("📅 Appointment Progress", f"{appt_pct:.1f}%",
                  f"{actual_appts:,} of {goals['appointments']:,} target")
        st.progress(int(appt_pct))

    # ── Department KPI table ──────────────────────────────────
    st.divider()
    st.subheader("🏥 Department-level KPI Breakdown")
    dept_kpi = df.groupby('department').agg(
        Appointments = ('patient_id','count'),
        Revenue      = ('fee','sum'),
        No_Show_Rate = ('status', lambda x: (x=='No-show').mean()*100),
    ).reset_index()
    dept_kpi['Revenue_Goal_Share'] = (dept_kpi['Revenue'] / goals['revenue'] * 100).round(1)
    dept_kpi['NS_Status'] = dept_kpi['No_Show_Rate'].apply(
        lambda x: '✅ Good' if x <= goals['no_show_cap'] else '❌ Over Cap')
    st.dataframe(
        dept_kpi.style.format({'Revenue':'Rs {:,.0f}','No_Show_Rate':'{:.1f}%','Revenue_Goal_Share':'{:.1f}%'})
                      .background_gradient(subset=['No_Show_Rate'], cmap='RdYlGn_r'),
        use_container_width=True)


# ============================================================
# PAGE 13 — OUR DOCTORS  ★ UPGRADED AVATARS
# ============================================================
elif page == "🩺 Our Doctors":
    st.title("🩺 Our Medical Specialists")
    st.caption("Meet the team — expertise, availability, and live performance metrics.")

    for i in range(0, len(DOCTOR_INFO), 2):
        cols = st.columns(2)
        for j, col in enumerate(cols):
            if i+j >= len(DOCTOR_INFO): break
            d        = DOCTOR_INFO[i+j]
            doc_data = df[df['doctor'] == d['key']]
            with col:
                with st.container(border=True):
                    img_col, info_col = st.columns([1,2])
                    with img_col:
                        st.image(d['img'], width=120)
                    with info_col:
                        st.markdown(f"""
                        <p class='doc-name'>{d['name']}</p>
                        <p class='doc-spec'>{d['spec']}</p>
                        <div class='doc-meta'>
                          🏥 {d['dept']}<br>
                          🎓 {d['edu']}<br>
                          ⏱️ {d['exp']} experience<br>
                          🕐 {d['timing']}
                        </div>""", unsafe_allow_html=True)
                    if not doc_data.empty:
                        ns   = (doc_data['status']=='No-show').mean()*100
                        rev  = doc_data['fee'].sum()
                        appt = len(doc_data)
                        comp = (doc_data['status']=='Completed').mean()*100
                        dm1,dm2,dm3,dm4 = st.columns(4)
                        dm1.metric("📅 Appts", appt)
                        dm2.metric("💰 Revenue", f"Rs {rev:,}")
                        dm3.metric("✅ Done", f"{comp:.0f}%")
                        dm4.metric("⚠️ No-show", f"{ns:.1f}%")


# ============================================================
# PAGE 14 — SCHEDULE HEATMAP  ★ NEW
# ============================================================
elif page == "🗓️ Schedule Heatmap":
    st.title("🗓️ Doctor Schedule Heatmap")
    st.caption("GitHub-style appointment density calendar — spot overloaded days and quiet periods at a glance.")

    view_mode = st.radio("View", ["Individual Doctor","All Doctors Combined"], horizontal=True)

    if view_mode == "Individual Doctor":
        doctor_sel = st.selectbox("Select Doctor", df['doctor'].unique())
        hmap_df = df[df['doctor']==doctor_sel].copy()
    else:
        hmap_df = df.copy()

    # ── Weekly heatmap (weeks × day of week) ─────────────────
    hmap_df['week_num']   = hmap_df['appointment_date'].dt.isocalendar().week.astype(int)
    hmap_df['day_of_week']= hmap_df['appointment_date'].dt.dayofweek

    heat_pivot = (hmap_df.groupby(['week_num','day_of_week']).size()
                         .unstack(fill_value=0)
                         .reindex(columns=[0,1,2,3,4,5,6], fill_value=0))
    heat_pivot.columns = ['Mon','Tue','Wed','Thu','Fri','Sat','Sun']

    fig_heat = px.imshow(
        heat_pivot.T,
        labels=dict(x="Week Number", y="Day of Week", color="Appointments"),
        color_continuous_scale='Blues', aspect='auto',
        title=f"Appointment Heatmap — {'All Doctors' if view_mode=='All Doctors Combined' else doctor_sel}",
    )
    fig_heat.update_layout(height=300, margin=dict(t=50,b=20,l=20,r=20))
    st.plotly_chart(fig_heat, use_container_width=True)

    # ── Hourly heatmap ────────────────────────────────────────
    st.subheader("⏰ Hour × Day Demand Heatmap")
    hour_heat = (hmap_df.groupby(['day_of_week','hour']).size()
                         .unstack(fill_value=0))
    hour_heat.index = ['Mon','Tue','Wed','Thu','Fri','Sat','Sun'][:len(hour_heat)]

    fig_hour = px.imshow(
        hour_heat, color_continuous_scale='Reds', aspect='auto',
        labels=dict(x="Hour", y="Day", color="Appointments"),
        title="Busiest hours per day — darker = more appointments",
    )
    fig_hour.update_layout(height=280, margin=dict(t=50,b=20,l=20,r=20))
    st.plotly_chart(fig_hour, use_container_width=True)

    # ── Click drill-down ──────────────────────────────────────
    st.divider()
    st.subheader("📋 Filter Appointments by Day")
    day_sel = st.selectbox("Select Day", ['Monday','Tuesday','Wednesday','Thursday','Friday','Saturday','Sunday'])
    day_num = ['Monday','Tuesday','Wednesday','Thursday','Friday','Saturday','Sunday'].index(day_sel)
    day_appts = hmap_df[hmap_df['day_of_week']==day_num]

    m1,m2,m3 = st.columns(3)
    m1.metric("📅 Total on this day", len(day_appts))
    m2.metric("💰 Revenue", f"Rs {day_appts['fee'].sum():,}")
    m3.metric("⚠️ No-show Rate", f"{(day_appts['status']=='No-show').mean()*100:.1f}%")

    st.dataframe(day_appts[['patient_name','department','doctor','hour','status','fee']]
                 .sort_values('hour'), use_container_width=True, height=280)

    # ── Status distribution per day ───────────────────────────
    st.divider()
    st.subheader("📊 Status Distribution by Day of Week")
    status_day = (df.groupby(['day','status']).size().unstack(fill_value=0))
    status_day = status_day.reindex(['Monday','Tuesday','Wednesday','Thursday','Friday','Saturday','Sunday'])
    st.bar_chart(status_day)


# ============================================================
# PAGE 15 — PAKISTAN CLINIC MAP
# ============================================================
elif page == "🗺️ Pakistan Clinic Map":
    st.title("🗺️ Pakistan Clinic Locations")
    st.caption("Click any clinic pin to view detailed analytics and send reports.")

    CLINIC_LOCATIONS = {
        "Lahore":     {"lat":31.5204,"lon":74.3587,"address":"Main Blvd, Gulberg III","phone":"042-35761234","email":"lahore@meditrack.pk"},
        "Karachi":    {"lat":24.8607,"lon":67.0011,"address":"Shahrah-e-Faisal, PECHS","phone":"021-34521890","email":"karachi@meditrack.pk"},
        "Islamabad":  {"lat":33.6844,"lon":73.0479,"address":"Blue Area, Jinnah Ave","phone":"051-2871345", "email":"islamabad@meditrack.pk"},
        "Peshawar":   {"lat":34.0151,"lon":71.5249,"address":"University Town, Ring Rd","phone":"091-5701234","email":"peshawar@meditrack.pk"},
        "Multan":     {"lat":30.1575,"lon":71.5249,"address":"Nishtar Road, Hussain Agahi","phone":"061-4501234","email":"multan@meditrack.pk"},
        "Rawalpindi": {"lat":33.5651,"lon":73.0169,"address":"Saddar Bazaar","phone":"051-5501678","email":"rawalpindi@meditrack.pk"},
        "Faisalabad": {"lat":31.4504,"lon":73.1350,"address":"Susan Road, D-Ground","phone":"041-8781234","email":"faisalabad@meditrack.pk"},
        "Quetta":     {"lat":30.1798,"lon":66.9750,"address":"Jinnah Road, Cantonment","phone":"081-2831234","email":"quetta@meditrack.pk"},
    }

    m = folium.Map(location=[30.3753,69.3451], zoom_start=5, tiles="CartoDB positron")
    city_rev = df.groupby('city')['fee'].sum()

    for city_name, info in CLINIC_LOCATIONS.items():
        if city_name not in df['city'].unique(): continue
        rev   = city_rev.get(city_name,0)
        appts = len(df[df['city']==city_name])
        ns    = (df[df['city']==city_name]['status']=='No-show').mean()*100
        max_r = city_rev.max()
        color = "green" if rev>=max_r*0.7 else ("blue" if rev>=max_r*0.4 else "orange")
        icon  = "star" if rev>=max_r*0.7 else "info-sign"

        popup_html = f"""
        <div style='font-family:Segoe UI,sans-serif;min-width:220px;'>
          <h4 style='margin:0 0 6px;color:#1a73e8;'>🏥 MediTrack — {city_name}</h4><hr style='margin:4px 0;'>
          <b>📍</b> {info['address']}<br><b>📞</b> {info['phone']}<br>
          <b>💰 Revenue:</b> Rs {rev:,.0f}<br><b>📅 Appts:</b> {appts:,}<br>
          <b>⚠️ No-show:</b> {ns:.1f}%
        </div>"""

        folium.Marker(location=[info['lat'],info['lon']],
                      popup=folium.Popup(popup_html, max_width=260),
                      tooltip=f"🏥 {city_name} — Rs {rev:,.0f}",
                      icon=folium.Icon(color=color, icon=icon, prefix='glyphicon')
                      ).add_to(m)

    st_folium(m, width=None, height=460)

    st.divider()
    selected_city = st.selectbox("📍 View City Details:", [c for c in CLINIC_LOCATIONS if c in df['city'].unique()])
    if selected_city:
        info       = CLINIC_LOCATIONS[selected_city]
        city_df    = df[df['city']==selected_city]
        total_rev  = city_df['fee'].sum()
        total_appt = len(city_df)
        uniq_pts   = city_df['patient_name'].nunique()
        avg_fee    = city_df['fee'].mean()
        ns_rate    = (city_df['status']=='No-show').mean()*100
        lost_rev   = city_df[city_df['status']=='No-show']['fee'].sum()

        sc1,sc2,sc3,sc4 = st.columns(4)
        sc1.metric("💰 Revenue",    f"Rs {total_rev:,}")
        sc2.metric("📅 Appts",      f"{total_appt:,}")
        sc3.metric("👥 Patients",   f"{uniq_pts:,}")
        sc4.metric("⚠️ No-show %", f"{ns_rate:.1f}%")

        st.info(f"📍 {info['address']} | 📞 {info['phone']}")


# ============================================================
# PAGE 16 — PDF REPORTS  ★ NEW
# ============================================================
elif page == "📄 PDF Reports":
    st.title("📄 PDF Report Generator")
    st.caption("Generate a professional branded management report with one click — ready for board meetings.")

    # ── Report preview ─────────────────────────────────────────
    total_rev  = df['fee'].sum()
    earned_rev = df[df['status']=='Completed']['fee'].sum()
    lost_rev   = df[df['status']=='No-show']['fee'].sum()
    ns_rate    = (df['status']=='No-show').mean()*100
    comp_rate  = (df['status']=='Completed').mean()*100

    st.subheader("📋 Report Preview")
    pv1,pv2,pv3,pv4 = st.columns(4)
    pv1.metric("Total Revenue",      f"Rs {total_rev:,}")
    pv2.metric("Earned Revenue",     f"Rs {earned_rev:,}")
    pv3.metric("Lost to No-shows",   f"Rs {lost_rev:,}")
    pv4.metric("No-show Rate",       f"{ns_rate:.1f}%")

    st.info("""📄 **Report includes:**
    - Clinic KPI Summary (revenue, appointments, rates)
    - Department Performance Table
    - Doctor Performance Table
    - City Revenue Summary
    - Management Intelligence Insights""")

    st.divider()
    col1, col2 = st.columns(2)
    with col1:
        report_title = st.text_input("Report Title", value="MediTrack A+ Management Report")
    with col2:
        report_date = st.date_input("Report Date", value=datetime.today())

    if st.button("📥 Generate & Download PDF Report", type="primary", use_container_width=True):
        if not FPDF_OK:
            st.error("❌ `fpdf2` is not installed. Run: `pip install fpdf2`")
        else:
            with st.spinner("🖨️ Generating professional PDF report…"):
                pdf_bytes = generate_pdf(df)
            if pdf_bytes:
                st.success("✅ PDF report generated successfully!")
                st.download_button(
                    label="📥 Download PDF Report",
                    data=pdf_bytes,
                    file_name=f"meditrack_report_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf",
                    mime="application/pdf",
                    use_container_width=True,
                )
                st.balloons()
            else:
                st.error("Failed to generate PDF. Check your fpdf2 installation.")

    st.divider()
    st.subheader("📊 What's In This Report")

    dept = df.groupby('department').agg(
        Appointments=('patient_id','count'),
        Revenue=('fee','sum'),
        No_Show_Rate=('status', lambda x: (x=='No-show').mean()*100),
    ).reset_index().sort_values('No_Show_Rate', ascending=False)

    st.dataframe(dept.style.format({'Revenue':'Rs {:,.0f}','No_Show_Rate':'{:.1f}%'})
                           .background_gradient(subset=['No_Show_Rate'], cmap='RdYlGn_r'),
                 use_container_width=True)

    doc_perf = df.groupby(['doctor','specialization']).agg(
        Appointments=('patient_id','count'),
        Revenue=('fee','sum'),
        No_Show_Rate=('status', lambda x: (x=='No-show').mean()*100),
    ).reset_index()
    st.dataframe(doc_perf.style.format({'Revenue':'Rs {:,.0f}','No_Show_Rate':'{:.1f}%'})
                               .background_gradient(subset=['No_Show_Rate'], cmap='RdYlGn_r'),
                 use_container_width=True)