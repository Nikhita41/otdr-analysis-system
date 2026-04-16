import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import time
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
import tempfile
import os

# PAGE CONFIG MUST BE FIRST
st.set_page_config(page_title="OTDR Dashboard", layout="wide")

from read_otdr import read_otdr_file
from process_data import process_otdr_data
from detect_event import detect_events

# ---------------- LOGIN ----------------
def login():
    st.title("🔐 OTDR Monitoring System Login")

    username = st.text_input("Username")
    password = st.text_input("Password", type="password")

    if st.button("Login"):
        if username == "admin" and password == "admin123":
            st.session_state["login"] = True
            st.rerun()
        else:
            st.error("Invalid login")

if "login" not in st.session_state:
    st.session_state["login"] = False

if not st.session_state["login"]:
    login()
    st.stop()

# ---------------- MAIN DASHBOARD ----------------

st.title("📡 COMPANY NAME - OTDR SMART FIBER MONITORING SYSTEM")

st.sidebar.title("Control Panel")
system_budget = st.sidebar.slider("System Budget (dB)", 20, 40, 28)
uploaded_file = st.sidebar.file_uploader("Upload OTDR File", type=["xlsx"])

if uploaded_file is not None:

    # Loading animation - faster and more responsive
    st.subheader("Analyzing Fiber Link...")
    progress = st.progress(0)
    status_text = st.empty()
    
    for i in range(100):
        progress.progress(i + 1)
        status_text.text(f"Processing: {i+1}%")
    
    status_text.text("✅ Analysis Complete!")
    progress.progress(100)

    raw_df = read_otdr_file(uploaded_file)
    df = process_otdr_data(raw_df)

    (major_events, minor_events,
     bend_count, break_count, connector_count, splice_count,
     dead_zones, fiber_length, total_loss,
     attenuation) = detect_events(df)

    margin = system_budget - total_loss

    # ---------------- SEVERITY ----------------
    if margin < 0:
        severity = "CRITICAL"
    elif break_count > 0 and margin < 5:
        severity = "CRITICAL"
    elif margin < 3:
        severity = "WARNING"
    elif break_count > 0:
        severity = "HIGH"
    elif attenuation > 0.8:
        severity = "MEDIUM"
    else:
        severity = "GOOD"

    # Severity Banner
    if severity == "GOOD":
        st.success("🟢 LINK STATUS: GOOD")
    elif severity == "MEDIUM":
        st.warning("🟡 LINK STATUS: MAINTENANCE REQUIRED")
    elif severity == "HIGH":
        st.error("🟠 LINK STATUS: REPAIR REQUIRED")
    elif severity == "WARNING":
        st.warning("🟣 LINK STATUS: LOW MARGIN")
    elif severity == "CRITICAL":
        st.error("🔴 LINK STATUS: CRITICAL FAILURE")

    # ---------------- KPI CARDS ----------------
    st.subheader("Network KPIs")
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Fiber Length (km)", f"{fiber_length:.2f}")
    col2.metric("Total Loss (dB)", f"{total_loss:.2f}")
    col3.metric("Power Margin (dB)", f"{margin:.2f}")
    col4.metric("Attenuation (dB/km)", f"{attenuation:.2f}")

    # ---------------- GAUGE ----------------
    fig_gauge = go.Figure(go.Indicator(
        mode="gauge+number",
        value=margin,
        title={'text': "Power Margin"},
        gauge={
            'axis': {'range': [-5, 15]},
            'bar': {'color': "cyan"},
            'steps': [
                {'range': [-5, 0], 'color': "red"},
                {'range': [0, 3], 'color': "orange"},
                {'range': [3, 6], 'color': "yellow"},
                {'range': [6, 15], 'color': "green"}
            ]
        }
    ))
    st.plotly_chart(fig_gauge, use_container_width=True)

    # ---------------- GRAPH TABS ----------------
    tab1, tab2, tab3, tab4 = st.tabs([
        "OTDR Trace",
        "Loss Analysis",
        "Fault Distribution",
        "Fiber Route Map"
    ])

    # OTDR TRACE WITH BLINKING FAULTS
    with tab1:
        fig = px.line(df, x="Distance", y="Power", title="OTDR Trace")

        for event in major_events:
            fig.add_scatter(x=[event[1]], y=[-5],
                            mode="markers",
                            marker=dict(size=12, color="red"),
                            name=event[0])

        st.plotly_chart(fig, use_container_width=True)

    # LOSS GRAPH
    with tab2:
        fig2 = px.area(df, x="Distance", y="Loss", title="Loss vs Distance")
        st.plotly_chart(fig2, use_container_width=True)

    # BAR + PIE
    fault_data = {
        "Break": break_count,
        "Bend": bend_count,
        "Splice": splice_count,
        "Connector": connector_count
    }

    fault_df = pd.DataFrame(list(fault_data.items()), columns=["Fault", "Count"])

    with tab3:
        colA, colB = st.columns(2)
        with colA:
            fig3 = px.bar(fault_df, x="Fault", y="Count", color="Fault")
            st.plotly_chart(fig3, use_container_width=True)
        with colB:
            fig4 = px.pie(fault_df, values="Count", names="Fault")
            st.plotly_chart(fig4, use_container_width=True)

    # FIBER ROUTE MAP (SIMULATED)
    with tab4:
        map_data = pd.DataFrame({
            "lat": [13.0827, 13.1, 13.12, 13.15],
            "lon": [80.2707, 80.28, 80.29, 80.30]
        })
        st.map(map_data)

    # ---------------- TABLES ----------------
    with st.expander("Major Events"):
        if major_events:
            st.table(pd.DataFrame(major_events, columns=["Type", "Distance", "Loss"]))

    with st.expander("Maintenance Zones"):
        if minor_events:
            st.table(pd.DataFrame(minor_events, columns=["Type", "Distance", "Loss"]))

    with st.expander("Dead Zones"):
        for dz in dead_zones:
            st.write(f"Dead zone from {dz[0]:.2f} km to {dz[1]:.2f} km")

    # ---------------- PDF REPORT ----------------
    def create_pdf():
        temp_file = tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.pdf')
        temp_path = temp_file.name
        temp_file.close()
        
        c = canvas.Canvas(temp_path, pagesize=letter)
        c.drawString(100, 750, "OTDR Link Report")
        c.drawString(100, 720, f"Fiber Length: {fiber_length:.2f} km")
        c.drawString(100, 700, f"Total Loss: {total_loss:.2f} dB")
        c.drawString(100, 680, f"Margin: {margin:.2f} dB")
        c.drawString(100, 660, f"Severity: {severity}")
        c.drawString(100, 640, f"Status: {severity}")
        c.save()
        return temp_path

    pdf_file = create_pdf()

    with open(pdf_file, "rb") as f:
        pdf_bytes = f.read()
        st.download_button(
            label="📥 Download PDF Report",
            data=pdf_bytes,
            file_name="OTDR_Report.pdf",
            mime="application/pdf"
        )

    # ---------------- FINAL SUMMARY ----------------
    st.subheader("Final Decision")

    if severity == "GOOD":
        st.success("Fiber link is healthy and ready for service.")
    elif severity == "MEDIUM":
        st.warning("Maintenance recommended.")
    elif severity == "HIGH":
        st.error("Repair required.")
    elif severity == "WARNING":
        st.warning("Low margin. Link unstable.")
    elif severity == "CRITICAL":
        st.error("Immediate repair required. Link will fail.")