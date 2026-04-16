import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import time
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader
from io import BytesIO

from read_otdr import read_otdr_file
from process_data import process_otdr_data
from detect_event import detect_events

st.set_page_config(page_title="OTDR Dashboard", layout="wide")
st.title("📡 OTDR SMART FIBER LINK MONITORING")

# ---------------- SIDEBAR ----------------
st.sidebar.header("Analysis Settings")
system_budget = st.sidebar.slider("System Budget (dB)", 20, 40, 28)
attenuation_threshold = st.sidebar.slider("Attenuation Threshold (dB/km)", 0.2, 1.5, 0.8)
uploaded_file = st.sidebar.file_uploader("Upload OTDR Excel File", type=["xlsx"])

# -------- MERGE CLOSE EVENTS FUNCTION --------
def merge_close_events(events, threshold=0.2):
    if not events:
        return []
    events = sorted(events, key=lambda x: x[1])
    merged = [events[0]]
    for current in events[1:]:
        last = merged[-1]
        if abs(current[1] - last[1]) < threshold:
            if current[2] > last[2]:
                merged[-1] = current
        else:
            merged.append(current)
    return merged

if uploaded_file is not None:

    # Loading bar
    st.subheader("Analyzing Fiber Link...")
    progress = st.progress(0)
    for i in range(100):
        time.sleep(0.01)
        progress.progress(i + 1)

    raw_df = read_otdr_file(uploaded_file)
    df = process_otdr_data(raw_df)

    (major_events, minor_events,
     bend_count, break_count, connector_count, splice_count,
     dead_zones, fiber_length, total_loss,
     attenuation) = detect_events(df)

    # -------- FIX FIBER LENGTH UNIT --------
    if fiber_length < 1:
        fiber_length = fiber_length * 1000
    if fiber_length > 200:
        fiber_length = fiber_length / 1000

    # -------- MERGE EVENTS --------
    major_events = merge_close_events(major_events)
    minor_events = merge_close_events(minor_events)

    margin = system_budget - total_loss

    # -------- SEVERITY LOGIC --------
    if margin < 0:
        severity = "CRITICAL"
        message = "Link will fail. Loss exceeds system budget."
    elif margin < 3:
        severity = "WARNING"
        message = "Low power margin. Link may become unstable."
    elif break_count > 0:
        severity = "HIGH"
        message = "Major physical faults detected. Repair required."
    elif attenuation > attenuation_threshold:
        severity = "MEDIUM"
        message = "High attenuation. Maintenance required."
    elif margin <= 6:
        severity = "GOOD"
        message = "Link working but margin low. Maintenance recommended."
    else:
        severity = "GOOD"
        message = "Link is healthy."

    if severity in ["CRITICAL", "HIGH"]:
        decision = "NOT ACCEPTABLE"
    else:
        decision = "ACCEPTABLE"

    # -------- REPORT SECTION --------
    st.header("📄 OTDR LINK ANALYSIS REPORT")

    st.write(f"**Fiber Length:** {fiber_length:.2f} km")
    st.write(f"**Total Loss:** {total_loss:.2f} dB")
    st.write(f"**Power Margin:** {margin:.2f} dB")
    st.write(f"**Attenuation:** {attenuation:.2f} dB/km")

    st.subheader("Power Budget")
    budget_df = pd.DataFrame({
        "Parameter": ["System Budget", "Measured Loss", "Available Margin"],
        "Value (dB)": [system_budget, total_loss, margin]
    })
    st.table(budget_df)

    st.subheader("Event Statistics")
    stats_df = pd.DataFrame({
        "Event Type": ["Break", "Bend", "Splice", "Connector"],
        "Count": [break_count, bend_count, splice_count, connector_count]
    })
    st.table(stats_df)

    # Collapsible sections
    with st.expander("📍 Major Events Table"):
        if major_events:
            st.table(pd.DataFrame(major_events, columns=["Type", "Distance (km)", "Loss (dB)"]))
        else:
            st.write("No major events")

    with st.expander("🔧 Maintenance Zones"):
        if minor_events:
            st.table(pd.DataFrame(minor_events, columns=["Type", "Distance (km)", "Loss (dB)"]))
        else:
            st.write("No maintenance zones")

    with st.expander("⚠ Dead Zones"):
        if dead_zones:
            for dz in dead_zones:
                st.write(f"Dead zone from {dz[0]:.2f} km to {dz[1]:.2f} km")
        else:
            st.write("No dead zones")

    st.subheader("Severity Analysis")
    st.write(f"**Severity:** {severity}")
    st.write(message)
    st.write(f"**Link Decision:** {decision}")

    # -------- GRAPHS --------
    st.header("📉 Graph Analysis")

    tab1, tab2, tab3 = st.tabs([
        "OTDR Trace",
        "Loss vs Distance",
        "Fault Distribution"
    ])

    def get_power(distance):
        idx = (df["Distance"] - distance).abs().idxmin()
        return df.loc[idx, "Power"]

    # OTDR TRACE
    with tab1:
        fig1 = go.Figure()

        fig1.add_trace(go.Scatter(
            x=df["Distance"],
            y=df["Power"],
            mode="lines",
            line=dict(color="cyan", width=2),
            name="Fiber Trace"
        ))

        # Major events
        for event in major_events:
            event_type, dist, loss = event
            fig1.add_vline(x=dist, line_width=2, line_dash="dash", line_color="red")
            fig1.add_scatter(
                x=[dist],
                y=[get_power(dist)],
                mode="markers+text",
                marker=dict(size=12, color="red"),
                text=[event_type],
                textposition="top center",
                showlegend=False
            )

        # Minor events
        for event in minor_events:
            event_type, dist, loss = event
            fig1.add_vline(x=dist, line_width=1, line_dash="dot", line_color="orange")
            fig1.add_scatter(
                x=[dist],
                y=[get_power(dist)],
                mode="markers+text",
                marker=dict(size=8, color="orange"),
                text=[event_type],
                textposition="bottom center",
                showlegend=False
            )

        fig1.update_layout(
            template="plotly_dark",
            title="OTDR Trace",
            xaxis_title="Distance (km)",
            yaxis_title="Power (dB)"
        )

        st.plotly_chart(fig1, use_container_width=True)

    # LOSS GRAPH
    with tab2:
        fig2 = px.line(df, x="Distance", y="Loss", markers=True,
                       title="Loss vs Distance")
        st.plotly_chart(fig2, use_container_width=True)

    # FAULT DISTRIBUTION
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
            st.plotly_chart(px.bar(fault_df, x="Fault", y="Count", color="Fault"),
                            use_container_width=True)
        with colB:
            st.plotly_chart(px.pie(fault_df, values="Count", names="Fault", hole=0.5),
                            use_container_width=True)

    # -------- PDF --------
    st.header("📄 Download Report")

    if st.button("Download PDF Report"):

        pdf_buffer = BytesIO()
        c = canvas.Canvas(pdf_buffer, pagesize=letter)
        width, height = letter

        c.setFont("Helvetica-Bold", 16)
        c.drawString(120, height - 40, "OTDR LINK ANALYSIS REPORT")

        c.setFont("Helvetica", 11)
        y = height - 80

        lines = [
            f"Fiber Length: {fiber_length:.2f} km",
            f"Total Loss: {total_loss:.2f} dB",
            f"Power Margin: {margin:.2f} dB",
            f"Attenuation: {attenuation:.2f} dB/km",
            "",
            "Event Statistics:",
            f"Breaks: {break_count}",
            f"Bends: {bend_count}",
            f"Splices: {splice_count}",
            f"Connectors: {connector_count}",
            "",
            f"Severity: {severity}",
            f"Decision: {decision}",
            "",
            "Summary:",
            message
        ]

        for line in lines:
            c.drawString(50, y, line)
            y -= 18

        img_buffer = BytesIO()
        fig1.write_image(img_buffer, format="png")
        img_buffer.seek(0)
        c.drawImage(ImageReader(img_buffer), 50, 80, width=500, height=200)

        c.save()
        pdf_bytes = pdf_buffer.getvalue()

        st.download_button(
            label="📥 Download PDF",
            data=pdf_bytes,
            file_name="OTDR_Report.pdf",
            mime="application/pdf"
        )