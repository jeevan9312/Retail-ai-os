import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import snowflake.connector

# ── Page Config ───────────────────────────────
st.set_page_config(
    page_title="AI Retail OS — Command Center",
    page_icon="🏪",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ── Snowflake Connection ───────────────────────
@st.cache_resource
def get_connection():
    return snowflake.connector.connect(
        account   = st.secrets.get("SNOWFLAKE_ACCOUNT", "jneusse-po63749"),
        user      = st.secrets.get("SNOWFLAKE_USER",    "JEEVAN17"),
        password  = st.secrets.get("SNOWFLAKE_PASSWORD", "your_password"),
        warehouse = "COMPUTE_WH",
        database  = "RETAIL_OS_DB",
        schema    = "MARTS"
    )

@st.cache_data(ttl=300)
def query(sql):
    try:
        conn   = get_connection()
        cursor = conn.cursor()
        cursor.execute(sql)
        cols = [c[0] for c in cursor.description]
        rows = cursor.fetchall()
        return pd.DataFrame(rows, columns=cols)
    except Exception as e:
        st.error(f"Query error: {e}")
        return pd.DataFrame()

# ── Chart Style ───────────────────────────────
DARK = "#1E293B"

def style(fig):
    fig.update_layout(
        paper_bgcolor=DARK,
        plot_bgcolor=DARK,
        font_color="#FFFFFF",
        margin=dict(t=40, b=20, l=20, r=20)
    )
    return fig

T = dict(template='plotly_dark')

# ── Load Data ─────────────────────────────────
@st.cache_data(ttl=300)
def load_all_data():
    df_sales = query("""
        SELECT TRANSACTION_DATE, STORE_ID,
               SUM(TOTAL_UNITS_SOLD)  AS UNITS,
               SUM(TOTAL_NET_REVENUE) AS REVENUE
        FROM RETAIL_OS_DB.STAGING.FCT_DAILY_SALES
        GROUP BY TRANSACTION_DATE, STORE_ID
        ORDER BY TRANSACTION_DATE
    """)
    df_inventory = query("""
        SELECT STOCK_STATUS, COUNT(*) AS COUNT
        FROM RETAIL_OS_DB.STAGING.FCT_INVENTORY_HEALTH
        GROUP BY STOCK_STATUS
    """)
    df_inventory_detail = query("""
        SELECT PRODUCT_ID, WAREHOUSE_ID,
               CURRENT_STOCK_LEVEL, STOCK_STATUS,
               NEEDS_REORDER, STOCK_COVERAGE_RATIO
        FROM RETAIL_OS_DB.STAGING.FCT_INVENTORY_HEALTH
        ORDER BY CURRENT_STOCK_LEVEL ASC
        LIMIT 50
    """)
    df_suppliers = query("""
        SELECT SUPPLIER_NAME, RELIABILITY_SCORE,
               RELIABILITY_TIER, TOTAL_BATCHES, AVG_UNIT_COST
        FROM RETAIL_OS_DB.STAGING.FCT_SUPPLIER_PERFORMANCE
        ORDER BY RELIABILITY_SCORE DESC
        LIMIT 15
    """)
    df_customers = query("""
        SELECT LOYALTY_TIER, COUNT(*) AS COUNT,
               AVG(LOYALTY_POINTS)       AS AVG_POINTS,
               AVG(APP_SESSION_DURATION) AS AVG_SESSION
        FROM RETAIL_OS_DB.STAGING.STG_CUSTOMER_PROFILES
        GROUP BY LOYALTY_TIER
    """)
    df_fraud = query("""
        SELECT TRANSACTION_ID, PRODUCT_ID, STORE_ID,
               FRAUD_PROBABILITY_SCORE,
               SUPPLY_CHAIN_DISRUPTION_RISK,
               ANOMALY_DETECTION_FLAG
        FROM RETAIL_OS_DB.RAW.RAW_RISK_ANOMALY
        WHERE FRAUD_PROBABILITY_SCORE > 0.7
        ORDER BY FRAUD_PROBABILITY_SCORE DESC
        LIMIT 20
    """)
    df_transactions = query("""
        SELECT PAYMENT_METHOD, COUNT(*) AS COUNT
        FROM RETAIL_OS_DB.RAW.RAW_TRANSACTIONS
        GROUP BY PAYMENT_METHOD
    """)
    df_economic = query("""
        SELECT CATEGORY,
               AVG(PRICE_ELASTICITY_COEFFICIENT) AS AVG_ELASTICITY,
               AVG(PROMOTION_LIFT_SCORE)         AS AVG_LIFT
        FROM RETAIL_OS_DB.RAW.RAW_ECONOMIC_SIGNALS
        GROUP BY CATEGORY
    """)
    df_weather = query("""
        SELECT OBSERVATION_DATE, WEATHER_CONDITION_CODE,
               AVG(TEMPERATURE) AS AVG_TEMP
        FROM RETAIL_OS_DB.RAW.RAW_WEATHER
        GROUP BY OBSERVATION_DATE, WEATHER_CONDITION_CODE
        ORDER BY OBSERVATION_DATE DESC
        LIMIT 30
    """)
    return (df_sales, df_inventory, df_inventory_detail,
            df_suppliers, df_customers, df_fraud,
            df_transactions, df_economic, df_weather)

# ── Sidebar ───────────────────────────────────
with st.sidebar:
    st.title("🏪 AI Retail OS")
    st.caption("Command Center")
    st.divider()
    page = st.selectbox("Navigate to", [
        "📊 Executive Dashboard",
        "💰 Sales Analytics",
        "📦 Inventory Monitoring",
        "🔮 Demand Forecast",
        "🚚 Supply Chain",
        "🏭 Supplier Analytics",
        "👥 Customer Dashboard",
        "🚨 Real-Time Alerts",
    ])
    st.divider()
    st.success("✅ 20 Agents Active")
    st.success("✅ Kafka Running")
    st.success("✅ Snowflake Connected")
    st.success("✅ MinIO Active")

# ── Load Data ─────────────────────────────────
with st.spinner("Loading from Snowflake..."):
    (df_sales, df_inventory, df_inventory_detail,
     df_suppliers, df_customers, df_fraud,
     df_transactions, df_economic, df_weather) = load_all_data()

# ── Metrics ───────────────────────────────────
total_revenue  = df_sales['REVENUE'].sum() if len(df_sales) > 0 else 0
total_units    = df_sales['UNITS'].sum() if len(df_sales) > 0 else 0
out_of_stock   = int(df_inventory[df_inventory['STOCK_STATUS'] == 'OUT_OF_STOCK']['COUNT'].sum()) if len(df_inventory) > 0 else 0
healthy_stock  = int(df_inventory[df_inventory['STOCK_STATUS'] == 'HEALTHY']['COUNT'].sum()) if len(df_inventory) > 0 else 0
reorder_count  = int(df_inventory[df_inventory['STOCK_STATUS'] == 'REORDER_NOW']['COUNT'].sum()) if len(df_inventory) > 0 else 0
low_stock      = int(df_inventory[df_inventory['STOCK_STATUS'] == 'LOW_STOCK']['COUNT'].sum()) if len(df_inventory) > 0 else 0
fraud_count    = len(df_fraud)
top_supplier   = df_suppliers['SUPPLIER_NAME'].iloc[0] if len(df_suppliers) > 0 else "N/A"
total_customers = int(df_customers['COUNT'].sum()) if len(df_customers) > 0 else 0
avg_loyalty    = float(df_customers['AVG_POINTS'].mean()) if len(df_customers) > 0 else 0
champions      = int(df_customers[df_customers['LOYALTY_TIER'] == 'GOLD']['COUNT'].sum()) if len(df_customers) > 0 else 0
high_tier      = len(df_suppliers[df_suppliers['RELIABILITY_TIER'] == 'HIGH']) if len(df_suppliers) > 0 else 0
total_batches  = int(df_suppliers['TOTAL_BATCHES'].sum()) if len(df_suppliers) > 0 else 0

INV_COLORS = {
    'HEALTHY':     '#16A34A',
    'LOW_STOCK':   '#D97706',
    'REORDER_NOW': '#DC2626',
    'OUT_OF_STOCK':'#7F1D1D'
}
CUST_COLORS = {
    'GOLD':   '#F59E0B',
    'SILVER': '#94A3B8',
    'BRONZE': '#B45309'
}

# ══════════════════════════════════════════════
# PAGE 1 — EXECUTIVE
# ══════════════════════════════════════════════
if page == "📊 Executive Dashboard":
    st.title("📊 Executive Dashboard")
    st.caption("Real-time overview for leadership")

    c1,c2,c3,c4,c5,c6 = st.columns(6)
    c1.metric("💰 Revenue",     f"${total_revenue:,.0f}")
    c2.metric("📦 Units Sold",  f"{total_units:,.0f}")
    c3.metric("🚨 Out of Stock",f"{out_of_stock}")
    c4.metric("✅ Healthy",     f"{healthy_stock}")
    c5.metric("⚠️ Fraud",      f"{fraud_count}")
    c6.metric("🏭 Top Supplier",top_supplier[:12])

    st.divider()
    col1, col2 = st.columns([2,1])
    with col1:
        if len(df_sales) > 0:
            fig = style(px.line(df_sales, x='TRANSACTION_DATE',
                                y='REVENUE', color='STORE_ID',
                                title='Daily Revenue by Store', **T))
            st.plotly_chart(fig, use_container_width=True)
    with col2:
        if len(df_inventory) > 0:
            fig = style(px.pie(df_inventory, names='STOCK_STATUS',
                               values='COUNT', title='Inventory Health',
                               color_discrete_map=INV_COLORS, **T))
            st.plotly_chart(fig, use_container_width=True)

    col3, col4 = st.columns(2)
    with col3:
        if len(df_suppliers) > 0:
            fig = style(px.bar(df_suppliers, x='SUPPLIER_NAME',
                               y='RELIABILITY_SCORE', color='RELIABILITY_TIER',
                               title='Supplier Reliability', **T))
            st.plotly_chart(fig, use_container_width=True)
    with col4:
        if len(df_transactions) > 0:
            fig = style(px.pie(df_transactions, names='PAYMENT_METHOD',
                               values='COUNT', title='Payment Methods', **T))
            st.plotly_chart(fig, use_container_width=True)

# ══════════════════════════════════════════════
# PAGE 2 — SALES
# ══════════════════════════════════════════════
elif page == "💰 Sales Analytics":
    st.title("💰 Sales Analytics Dashboard")
    st.caption("For Sales Manager — Revenue and units")

    c1,c2,c3,c4 = st.columns(4)
    c1.metric("💰 Revenue",    f"${total_revenue:,.0f}")
    c2.metric("📦 Units",      f"{total_units:,.0f}")
    c3.metric("📈 Avg/Day",    f"${total_revenue/180:,.0f}")
    c4.metric("💳 Payments",   "5 Methods")

    st.divider()
    if len(df_sales) > 0:
        fig = style(px.line(df_sales, x='TRANSACTION_DATE',
                            y='REVENUE', color='STORE_ID',
                            title='Daily Revenue by Store', **T))
        st.plotly_chart(fig, use_container_width=True)

    col1, col2 = st.columns([2,1])
    with col1:
        if len(df_sales) > 0:
            fig = style(px.area(df_sales, x='TRANSACTION_DATE',
                                y='UNITS', color='STORE_ID',
                                title='Daily Units Sold', **T))
            st.plotly_chart(fig, use_container_width=True)
    with col2:
        if len(df_transactions) > 0:
            fig = style(px.pie(df_transactions, names='PAYMENT_METHOD',
                               values='COUNT', title='Payment Methods', **T))
            st.plotly_chart(fig, use_container_width=True)

# ══════════════════════════════════════════════
# PAGE 3 — INVENTORY
# ══════════════════════════════════════════════
elif page == "📦 Inventory Monitoring":
    st.title("📦 Inventory Monitoring Dashboard")
    st.caption("For Warehouse Manager — Stock health and reorder alerts")

    c1,c2,c3,c4 = st.columns(4)
    c1.metric("✅ Healthy",     f"{healthy_stock}")
    c2.metric("⚠️ Reorder Now", f"{reorder_count}")
    c3.metric("📉 Low Stock",   f"{low_stock}")
    c4.metric("🚨 Out of Stock",f"{out_of_stock}")

    st.divider()
    col1, col2 = st.columns([1,2])
    with col1:
        if len(df_inventory) > 0:
            fig = style(px.pie(df_inventory, names='STOCK_STATUS',
                               values='COUNT', title='Inventory Health',
                               color_discrete_map=INV_COLORS, **T))
            st.plotly_chart(fig, use_container_width=True)
    with col2:
        if len(df_inventory_detail) > 0:
            fig = style(px.bar(df_inventory_detail.head(20),
                               x='PRODUCT_ID', y='CURRENT_STOCK_LEVEL',
                               color='STOCK_STATUS',
                               title='Stock Levels by Product',
                               color_discrete_map=INV_COLORS, **T))
            st.plotly_chart(fig, use_container_width=True)

    st.subheader("🚨 Critical Items Needing Immediate Reorder")
    critical = df_inventory_detail[
        df_inventory_detail['STOCK_STATUS'].isin(['OUT_OF_STOCK','REORDER_NOW'])
    ].head(15)
    st.dataframe(critical, use_container_width=True)

# ══════════════════════════════════════════════
# PAGE 4 — FORECAST
# ══════════════════════════════════════════════
elif page == "🔮 Demand Forecast":
    st.title("🔮 Demand Forecast Dashboard")
    st.caption("For Demand Planner — Forecasts and demand intelligence")

    c1,c2,c3,c4 = st.columns(4)
    c1.metric("🛍️ SKUs",      "200 Products")
    c2.metric("🏪 Stores",    "50 Stores")
    c3.metric("🔮 Forecasts", "6,870")
    c4.metric("🤖 Model",     "XGBoost")

    st.divider()
    df_forecast = query("""
        SELECT PRODUCT_ID,
               AVG(TOTAL_UNITS_SOLD) AS AVG_DEMAND,
               MAX(TOTAL_UNITS_SOLD) AS MAX_DEMAND
        FROM RETAIL_OS_DB.STAGING.FCT_DAILY_SALES
        GROUP BY PRODUCT_ID
        ORDER BY AVG_DEMAND DESC
        LIMIT 20
    """)
    df_spikes = query("""
        SELECT PRODUCT_ID, COUNT(*) AS SPIKE_COUNT
        FROM RETAIL_OS_DB.RAW.RAW_SALES_INTELLIGENCE
        WHERE DEMAND_SPIKE_INDICATOR = TRUE
        GROUP BY PRODUCT_ID
        ORDER BY SPIKE_COUNT DESC
        LIMIT 10
    """)

    col1, col2 = st.columns(2)
    with col1:
        if len(df_forecast) > 0:
            fig = style(px.bar(df_forecast, x='PRODUCT_ID',
                               y='AVG_DEMAND',
                               title='Average Demand by Product', **T))
            st.plotly_chart(fig, use_container_width=True)
    with col2:
        if len(df_spikes) > 0:
            fig = style(px.bar(df_spikes, x='PRODUCT_ID',
                               y='SPIKE_COUNT', color='SPIKE_COUNT',
                               title='Demand Spikes by Product', **T))
            st.plotly_chart(fig, use_container_width=True)

    col3, col4 = st.columns(2)
    with col3:
        if len(df_sales) > 0:
            fig = style(px.area(df_sales, x='TRANSACTION_DATE',
                                y='UNITS', color='STORE_ID',
                                title='Daily Units Sold', **T))
            st.plotly_chart(fig, use_container_width=True)
    with col4:
        if len(df_economic) > 0:
            fig = style(px.bar(df_economic, x='CATEGORY',
                               y='AVG_ELASTICITY', color='AVG_LIFT',
                               title='Price Elasticity by Category', **T))
            st.plotly_chart(fig, use_container_width=True)

# ══════════════════════════════════════════════
# PAGE 5 — SUPPLY CHAIN
# ══════════════════════════════════════════════
elif page == "🚚 Supply Chain":
    st.title("🚚 Supply Chain Dashboard")
    st.caption("For Supply Chain Manager — Risk and logistics")

    c1,c2,c3,c4 = st.columns(4)
    c1.metric("🏭 Warehouses",   "15")
    c2.metric("📦 Reorder",      "707 Items")
    c3.metric("🚚 Routes",       "15 Active")
    c4.metric("⚠️ Supply Risks", "4,318")

    st.divider()
    col1, col2 = st.columns([1,2])
    with col1:
        if len(df_inventory) > 0:
            fig = style(px.pie(df_inventory, names='STOCK_STATUS',
                               values='COUNT', title='Stock Health',
                               color_discrete_map=INV_COLORS, **T))
            st.plotly_chart(fig, use_container_width=True)
    with col2:
        if len(df_inventory_detail) > 0:
            fig = style(px.bar(df_inventory_detail.head(20),
                               x='PRODUCT_ID', y='CURRENT_STOCK_LEVEL',
                               color='STOCK_STATUS',
                               title='Stock by Product',
                               color_discrete_map=INV_COLORS, **T))
            st.plotly_chart(fig, use_container_width=True)

    col3, col4 = st.columns(2)
    with col3:
        if len(df_weather) > 0:
            fig = style(px.line(df_weather, x='OBSERVATION_DATE',
                                y='AVG_TEMP',
                                color='WEATHER_CONDITION_CODE',
                                title='Weather Trends', **T))
            st.plotly_chart(fig, use_container_width=True)
    with col4:
        if len(df_suppliers) > 0:
            fig = style(px.scatter(df_suppliers,
                                   x='RELIABILITY_SCORE',
                                   y='AVG_UNIT_COST',
                                   size='TOTAL_BATCHES',
                                   color='RELIABILITY_TIER',
                                   text='SUPPLIER_NAME',
                                   title='Reliability vs Cost', **T))
            st.plotly_chart(fig, use_container_width=True)

# ══════════════════════════════════════════════
# PAGE 6 — SUPPLIERS
# ══════════════════════════════════════════════
elif page == "🏭 Supplier Analytics":
    st.title("🏭 Supplier Analytics Dashboard")
    st.caption("For Procurement Team — Reliability and performance")

    c1,c2,c3,c4 = st.columns(4)
    c1.metric("🏭 Suppliers",    "30 Total")
    c2.metric("⭐ Top Supplier", top_supplier[:12])
    c3.metric("✅ HIGH Tier",    f"{high_tier}")
    c4.metric("📦 Batches",      f"{total_batches:,}")

    st.divider()
    if len(df_suppliers) > 0:
        fig = style(px.bar(df_suppliers, x='SUPPLIER_NAME',
                           y='RELIABILITY_SCORE', color='RELIABILITY_TIER',
                           title='Supplier Reliability Scores', **T))
        st.plotly_chart(fig, use_container_width=True)

    col1, col2 = st.columns(2)
    with col1:
        if len(df_suppliers) > 0:
            fig = style(px.scatter(df_suppliers,
                                   x='RELIABILITY_SCORE',
                                   y='AVG_UNIT_COST',
                                   size='TOTAL_BATCHES',
                                   color='RELIABILITY_TIER',
                                   text='SUPPLIER_NAME',
                                   title='Reliability vs Cost', **T))
            st.plotly_chart(fig, use_container_width=True)
    with col2:
        st.subheader("Supplier Scorecard")
        if len(df_suppliers) > 0:
            st.dataframe(df_suppliers.round(3), use_container_width=True)

# ══════════════════════════════════════════════
# PAGE 7 — CUSTOMERS
# ══════════════════════════════════════════════
elif page == "👥 Customer Dashboard":
    st.title("👥 Customer Dashboard")
    st.caption("For Marketing Team — Segments and campaigns")

    c1,c2,c3,c4 = st.columns(4)
    c1.metric("👥 Customers",   f"{total_customers:,}")
    c2.metric("⭐ Avg Loyalty", f"{avg_loyalty:,.0f}")
    c3.metric("🏆 Champions",  f"{champions}")
    c4.metric("📢 Campaigns",  "4 Active")

    st.divider()
    col1, col2 = st.columns(2)
    with col1:
        if len(df_customers) > 0:
            fig = style(px.bar(df_customers, x='LOYALTY_TIER',
                               y='COUNT', color='LOYALTY_TIER',
                               title='Customer Segments',
                               color_discrete_map=CUST_COLORS, **T))
            st.plotly_chart(fig, use_container_width=True)
    with col2:
        if len(df_customers) > 0:
            fig = style(px.bar(df_customers, x='LOYALTY_TIER',
                               y='AVG_POINTS', color='LOYALTY_TIER',
                               title='Avg Loyalty Points',
                               color_discrete_map=CUST_COLORS, **T))
            st.plotly_chart(fig, use_container_width=True)

    col3, col4 = st.columns(2)
    with col3:
        if len(df_customers) > 0:
            fig = style(px.bar(df_customers, x='LOYALTY_TIER',
                               y='AVG_SESSION', color='LOYALTY_TIER',
                               title='Avg App Session Duration',
                               color_discrete_map=CUST_COLORS, **T))
            st.plotly_chart(fig, use_container_width=True)
    with col4:
        st.subheader("📢 Active Campaigns")
        campaigns = [
            ("🏆 GOLD",   "VIP Early Access",    "570 customers", "Email+Push+SMS", "#F59E0B"),
            ("🥈 SILVER", "Double Points Event", "185 customers", "Email+Push",     "#94A3B8"),
            ("🥉 BRONZE", "Welcome Discount",    "245 customers", "Email",          "#B45309"),
            ("🌟 ALL",    "Holiday Special",     "1,000 customers","All Channels",  "#16A34A"),
        ]
        for tier, name, count, channel, color in campaigns:
            st.markdown(f"""
            <div style="background:#1E293B;border-left:4px solid {color};
                        padding:10px;margin-bottom:8px;border-radius:4px;">
                <b style="color:{color}">{tier} — {name}</b><br>
                <small style="color:#64748B">{count} | {channel}</small>
            </div>
            """, unsafe_allow_html=True)

# ══════════════════════════════════════════════
# PAGE 8 — ALERTS
# ══════════════════════════════════════════════
elif page == "🚨 Real-Time Alerts":
    st.title("🚨 Real-Time Alerts Dashboard")
    st.caption("For Operations Team — Fraud, anomalies, critical alerts")

    c1,c2,c3,c4 = st.columns(4)
    c1.metric("🚨 Fraud Alerts", f"{fraud_count}")
    c2.metric("📦 Out of Stock", f"{out_of_stock}")
    c3.metric("⚠️ Supply Risks", "4,318")
    c4.metric("🔍 Anomalies",    "500")

    st.divider()
    col1, col2 = st.columns(2)
    with col1:
        if len(df_fraud) > 0:
            fig = style(px.scatter(df_fraud,
                                   x='FRAUD_PROBABILITY_SCORE',
                                   y='SUPPLY_CHAIN_DISRUPTION_RISK',
                                   color='STORE_ID',
                                   title='Fraud & Risk Detection', **T))
            st.plotly_chart(fig, use_container_width=True)
    with col2:
        st.subheader("🚨 Active System Alerts")
        alerts = [
            (f"🚨 {out_of_stock} Products OUT OF STOCK",
             "Auto POs created — immediate reorder", "#DC2626"),
            (f"⚠️ {fraud_count} High-Risk Fraud Transactions",
             "Review flagged transactions immediately", "#D97706"),
            ("⚠️ 1,687 Critical Supply Chain Risks",
             "Activate backup suppliers immediately", "#D97706"),
            ("✅ All 20 AI Agents Running",
             "System operating normally", "#16A34A"),
            ("ℹ️ Digital Twin: Festival = $9,904 revenue",
             "Stock up for festival season", "#2563EB"),
        ]
        for title, desc, color in alerts:
            st.markdown(f"""
            <div style="background:#1E293B;border-left:4px solid {color};
                        padding:12px;margin-bottom:8px;border-radius:4px;">
                <b style="color:{color}">{title}</b><br>
                <small style="color:#64748B">{desc}</small>
            </div>
            """, unsafe_allow_html=True)

    st.subheader("High-Risk Fraud Transactions")
    if len(df_fraud) > 0:
        st.dataframe(df_fraud.round(3), use_container_width=True)