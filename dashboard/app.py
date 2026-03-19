import sys
sys.path.insert(0, '..')
import dash
from dash import dcc, html, Input, Output, dash_table
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import snowflake.connector
sys.path.insert(0, '../agents')
from config import SNOWFLAKE_CONFIG

app = dash.Dash(__name__, suppress_callback_exceptions=True)
app.title = "AI Retail OS — Command Center"

# ── Colors ────────────────────────────────────────────────
NAVY   = "#0F172A"
BLUE   = "#2563EB"
TEAL   = "#0D9488"
AMBER  = "#D97706"
GREEN  = "#16A34A"
RED    = "#DC2626"
PURPLE = "#7C3AED"
GRAY   = "#475569"
WHITE  = "#FFFFFF"
DARK   = "#1E293B"
CARD   = "#1E293B"

# ── Snowflake Query ───────────────────────────────────────
def query(sql):
    try:
        conn   = snowflake.connector.connect(**SNOWFLAKE_CONFIG)
        cursor = conn.cursor()
        cursor.execute(sql)
        cols   = [c[0] for c in cursor.description]
        rows   = cursor.fetchall()
        conn.close()
        return pd.DataFrame(rows, columns=cols)
    except Exception as e:
        print(f"Query error: {e}")
        return pd.DataFrame()

# ── Chart Style ───────────────────────────────────────────
chart_style = dict(template='plotly_dark')

def apply_style(fig):
    fig.update_layout(
        paper_bgcolor=CARD,
        plot_bgcolor=CARD,
        font_color=WHITE,
        margin=dict(t=40, b=20, l=20, r=20)
    )
    return fig

# ── Load All Data ─────────────────────────────────────────
print("Loading data from Snowflake...")

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
           RELIABILITY_TIER, TOTAL_BATCHES,
           AVG_UNIT_COST
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

df_weather = query("""
    SELECT OBSERVATION_DATE, WEATHER_CONDITION_CODE,
           AVG(TEMPERATURE)         AS AVG_TEMP,
           AVG(PRECIPITATION_LEVEL) AS AVG_RAIN
    FROM RETAIL_OS_DB.RAW.RAW_WEATHER
    GROUP BY OBSERVATION_DATE, WEATHER_CONDITION_CODE
    ORDER BY OBSERVATION_DATE DESC
    LIMIT 30
""")

df_competitor = query("""
    SELECT COMPETITOR_ID,
           AVG(COMPETITOR_PRICE)        AS AVG_PRICE,
           AVG(MARKET_SHARE_PERCENTAGE) AS AVG_SHARE,
           AVG(TREND_SCORE)             AS AVG_TREND
    FROM RETAIL_OS_DB.RAW.RAW_COMPETITOR_DATA
    GROUP BY COMPETITOR_ID
""")

df_transactions = query("""
    SELECT PAYMENT_METHOD, COUNT(*) AS COUNT
    FROM RETAIL_OS_DB.RAW.RAW_TRANSACTIONS
    GROUP BY PAYMENT_METHOD
""")

df_economic = query("""
    SELECT CATEGORY,
           AVG(PRICE_ELASTICITY_COEFFICIENT) AS AVG_ELASTICITY,
           AVG(PROMOTION_LIFT_SCORE)         AS AVG_LIFT,
           AVG(INVENTORY_TURNOVER_RATIO)     AS AVG_TURNOVER
    FROM RETAIL_OS_DB.RAW.RAW_ECONOMIC_SIGNALS
    GROUP BY CATEGORY
""")

print("Data loaded!")

# ── KPI Metrics ───────────────────────────────────────────
total_revenue = df_sales['REVENUE'].sum() if len(df_sales) > 0 else 0
total_units   = df_sales['UNITS'].sum() if len(df_sales) > 0 else 0
out_of_stock  = int(df_inventory[df_inventory['STOCK_STATUS'] == 'OUT_OF_STOCK']['COUNT'].sum()) if len(df_inventory) > 0 else 0
healthy_stock = int(df_inventory[df_inventory['STOCK_STATUS'] == 'HEALTHY']['COUNT'].sum()) if len(df_inventory) > 0 else 0
fraud_count   = len(df_fraud)
top_supplier  = df_suppliers['SUPPLIER_NAME'].iloc[0] if len(df_suppliers) > 0 else "N/A"

# ── Shared Styles ─────────────────────────────────────────
PAGE_STYLE = {
    'backgroundColor': NAVY,
    'minHeight': '100vh',
    'fontFamily': 'Arial, sans-serif',
    'color': WHITE
}

CARD_STYLE = {
    'backgroundColor': CARD,
    'borderRadius': '10px',
    'padding': '20px',
    'margin': '8px',
    'border': '1px solid #334155'
}

# ── KPI Card ──────────────────────────────────────────────
def kpi_card(title, value, color, icon=""):
    return html.Div(style={**CARD_STYLE, 'border': f'1px solid {color}',
                           'textAlign': 'center', 'flex': '1'}, children=[
        html.H2(f"{icon} {value}", style={'color': color, 'margin': '0', 'fontSize': '26px'}),
        html.P(title, style={'color': GRAY, 'margin': '4px 0 0 0', 'fontSize': '12px'})
    ])

# ── Build All Figures ─────────────────────────────────────
fig_revenue = apply_style(px.line(
    df_sales, x='TRANSACTION_DATE', y='REVENUE',
    color='STORE_ID', title='Daily Revenue by Store',
    **chart_style)) if len(df_sales) > 0 else go.Figure()

fig_inventory_pie = apply_style(px.pie(
    df_inventory, names='STOCK_STATUS', values='COUNT',
    title='Inventory Health Status',
    color_discrete_map={'HEALTHY': GREEN, 'LOW_STOCK': AMBER,
                        'REORDER_NOW': RED, 'OUT_OF_STOCK': '#7F1D1D'},
    **chart_style)) if len(df_inventory) > 0 else go.Figure()

fig_suppliers_bar = apply_style(px.bar(
    df_suppliers, x='SUPPLIER_NAME', y='RELIABILITY_SCORE',
    color='RELIABILITY_TIER', title='Supplier Reliability Scores',
    **chart_style)) if len(df_suppliers) > 0 else go.Figure()

fig_payment = apply_style(px.pie(
    df_transactions, names='PAYMENT_METHOD', values='COUNT',
    title='Payment Method Distribution',
    **chart_style)) if len(df_transactions) > 0 else go.Figure()

fig_customers = apply_style(px.bar(
    df_customers, x='LOYALTY_TIER', y='COUNT',
    color='LOYALTY_TIER', title='Customer Segments',
    color_discrete_map={'GOLD': '#F59E0B', 'SILVER': '#94A3B8', 'BRONZE': '#B45309'},
    **chart_style)) if len(df_customers) > 0 else go.Figure()

fig_fraud = apply_style(px.scatter(
    df_fraud,
    x='FRAUD_PROBABILITY_SCORE',
    y='SUPPLY_CHAIN_DISRUPTION_RISK',
    color='STORE_ID',
    title='Fraud & Risk Detection',
    labels={'FRAUD_PROBABILITY_SCORE': 'Fraud Score',
            'SUPPLY_CHAIN_DISRUPTION_RISK': 'Supply Risk'},
    **chart_style)) if len(df_fraud) > 0 else go.Figure()

fig_competitor = apply_style(px.bar(
    df_competitor, x='COMPETITOR_ID',
    y='AVG_PRICE', title='Competitor Average Prices',
    color='AVG_SHARE',
    **chart_style)) if len(df_competitor) > 0 else go.Figure()

fig_elasticity = apply_style(px.bar(
    df_economic, x='CATEGORY',
    y='AVG_ELASTICITY', title='Price Elasticity by Category',
    color='AVG_LIFT',
    **chart_style)) if len(df_economic) > 0 else go.Figure()

fig_weather = apply_style(px.line(
    df_weather, x='OBSERVATION_DATE',
    y='AVG_TEMP', color='WEATHER_CONDITION_CODE',
    title='Weather Trends',
    **chart_style)) if len(df_weather) > 0 else go.Figure()

fig_units = apply_style(px.area(
    df_sales, x='TRANSACTION_DATE', y='UNITS',
    color='STORE_ID', title='Daily Units Sold by Store',
    **chart_style)) if len(df_sales) > 0 else go.Figure()

fig_inventory_bar = apply_style(px.bar(
    df_inventory_detail.head(20),
    x='PRODUCT_ID', y='CURRENT_STOCK_LEVEL',
    color='STOCK_STATUS',
    title='Stock Levels by Product',
    color_discrete_map={'HEALTHY': GREEN, 'LOW_STOCK': AMBER,
                        'REORDER_NOW': RED, 'OUT_OF_STOCK': '#7F1D1D'},
    **chart_style)) if len(df_inventory_detail) > 0 else go.Figure()

fig_supplier_cost = apply_style(px.scatter(
    df_suppliers,
    x='RELIABILITY_SCORE', y='AVG_UNIT_COST',
    size='TOTAL_BATCHES', color='RELIABILITY_TIER',
    text='SUPPLIER_NAME',
    title='Supplier: Reliability vs Cost',
    **chart_style)) if len(df_suppliers) > 0 else go.Figure()

# ══════════════════════════════════════════════
# SIDEBAR NAVIGATION
# ══════════════════════════════════════════════
def sidebar():
    nav_items = [
        ("📊", "Executive",    "/"),
        ("💰", "Sales",        "/sales"),
        ("📦", "Inventory",    "/inventory"),
        ("🔮", "Forecast",     "/forecast"),
        ("🚚", "Supply Chain", "/supply"),
        ("🏭", "Suppliers",    "/suppliers"),
        ("👥", "Customers",    "/customers"),
        ("🚨", "Alerts",       "/alerts"),
    ]
    return html.Div(style={
        'width': '200px', 'minHeight': '100vh',
        'backgroundColor': DARK, 'padding': '0',
        'borderRight': '1px solid #334155',
        'position': 'fixed', 'top': '0', 'left': '0',
        'zIndex': '1000', 'overflowY': 'auto'
    }, children=[
        html.Div(style={'padding': '20px 16px', 'borderBottom': '1px solid #334155'},
                 children=[
            html.H3("🏪 AI Retail OS", style={'color': BLUE, 'margin': '0', 'fontSize': '16px'}),
            html.P("Command Center", style={'color': GRAY, 'margin': '4px 0 0 0', 'fontSize': '11px'})
        ]),
        html.Div(style={'padding': '12px 0'}, children=[
            dcc.Link(
                html.Div(style={
                    'padding': '12px 20px', 'cursor': 'pointer',
                    'display': 'flex', 'alignItems': 'center',
                    'gap': '10px', 'color': WHITE, 'fontSize': '14px'
                }, children=[html.Span(icon), html.Span(label)]),
                href=path, style={'textDecoration': 'none'}
            )
            for icon, label, path in nav_items
        ]),
        html.Div(style={'padding': '16px', 'borderTop': '1px solid #334155',
                        'marginTop': '20px'}, children=[
            html.P("✅ 20 Agents Active",      style={'color': GREEN, 'fontSize': '11px', 'margin': '2px 0'}),
            html.P("✅ Kafka Running",          style={'color': GREEN, 'fontSize': '11px', 'margin': '2px 0'}),
            html.P("✅ Snowflake Connected",    style={'color': GREEN, 'fontSize': '11px', 'margin': '2px 0'}),
            html.P("✅ MinIO Active",           style={'color': GREEN, 'fontSize': '11px', 'margin': '2px 0'}),
        ])
    ])

# ══════════════════════════════════════════════
# PAGE 1 — EXECUTIVE
# ══════════════════════════════════════════════
def page_executive():
    return html.Div([
        html.H2("📊 Executive Dashboard", style={'color': WHITE, 'margin': '0 0 4px 0'}),
        html.P("Real-time overview for leadership", style={'color': GRAY, 'margin': '0 0 20px 0', 'fontSize': '13px'}),
        html.Div(style={'display': 'flex', 'gap': '4px', 'marginBottom': '16px'}, children=[
            kpi_card("Total Revenue",  f"${total_revenue:,.0f}", BLUE,   "💰"),
            kpi_card("Units Sold",     f"{total_units:,.0f}",    GREEN,  "📦"),
            kpi_card("Out of Stock",   f"{out_of_stock}",        RED,    "🚨"),
            kpi_card("Healthy Stock",  f"{healthy_stock}",       TEAL,   "✅"),
            kpi_card("Fraud Alerts",   f"{fraud_count}",         AMBER,  "⚠️"),
            kpi_card("Top Supplier",   top_supplier[:12],        PURPLE, "🏭"),
        ]),
        html.Div(style={'display': 'flex', 'gap': '4px', 'marginBottom': '4px'}, children=[
            html.Div(style={**CARD_STYLE, 'flex': '2', 'margin': '4px'}, children=[dcc.Graph(figure=fig_revenue)]),
            html.Div(style={**CARD_STYLE, 'flex': '1', 'margin': '4px'}, children=[dcc.Graph(figure=fig_inventory_pie)]),
        ]),
        html.Div(style={'display': 'flex', 'gap': '4px'}, children=[
            html.Div(style={**CARD_STYLE, 'flex': '1', 'margin': '4px'}, children=[dcc.Graph(figure=fig_suppliers_bar)]),
            html.Div(style={**CARD_STYLE, 'flex': '1', 'margin': '4px'}, children=[dcc.Graph(figure=fig_payment)]),
        ]),
    ])

# ══════════════════════════════════════════════
# PAGE 2 — SALES
# ══════════════════════════════════════════════
def page_sales():
    return html.Div([
        html.H2("💰 Sales Analytics Dashboard", style={'color': WHITE, 'margin': '0 0 4px 0'}),
        html.P("For Sales Manager — Revenue, units, and payment trends", style={'color': GRAY, 'margin': '0 0 20px 0', 'fontSize': '13px'}),
        html.Div(style={'display': 'flex', 'gap': '4px', 'marginBottom': '16px'}, children=[
            kpi_card("Total Revenue",   f"${total_revenue:,.0f}",      BLUE,  "💰"),
            kpi_card("Total Units",     f"{total_units:,.0f}",          GREEN, "📦"),
            kpi_card("Avg Rev/Day",     f"${total_revenue/180:,.0f}",   TEAL,  "📈"),
            kpi_card("Payment Methods", "5 Types",                      AMBER, "💳"),
        ]),
        html.Div(style={**CARD_STYLE, 'marginBottom': '8px'}, children=[dcc.Graph(figure=fig_revenue, style={'height': '350px'})]),
        html.Div(style={'display': 'flex', 'gap': '4px'}, children=[
            html.Div(style={**CARD_STYLE, 'flex': '2', 'margin': '4px'}, children=[dcc.Graph(figure=fig_units)]),
            html.Div(style={**CARD_STYLE, 'flex': '1', 'margin': '4px'}, children=[dcc.Graph(figure=fig_payment)]),
        ]),
    ])

# ══════════════════════════════════════════════
# PAGE 3 — INVENTORY
# ══════════════════════════════════════════════
def page_inventory():
    reorder_count = int(df_inventory[df_inventory['STOCK_STATUS'] == 'REORDER_NOW']['COUNT'].sum()) if len(df_inventory) > 0 else 0
    low_stock     = int(df_inventory[df_inventory['STOCK_STATUS'] == 'LOW_STOCK']['COUNT'].sum()) if len(df_inventory) > 0 else 0
    critical_df   = df_inventory_detail[df_inventory_detail['STOCK_STATUS'].isin(['OUT_OF_STOCK', 'REORDER_NOW'])].head(15)

    return html.Div([
        html.H2("📦 Inventory Monitoring Dashboard", style={'color': WHITE, 'margin': '0 0 4px 0'}),
        html.P("For Warehouse Manager — Stock health and reorder alerts", style={'color': GRAY, 'margin': '0 0 20px 0', 'fontSize': '13px'}),
        html.Div(style={'display': 'flex', 'gap': '4px', 'marginBottom': '16px'}, children=[
            kpi_card("Healthy Items", f"{healthy_stock}", GREEN, "✅"),
            kpi_card("Reorder Now",   f"{reorder_count}", AMBER, "⚠️"),
            kpi_card("Low Stock",     f"{low_stock}",     AMBER, "📉"),
            kpi_card("Out of Stock",  f"{out_of_stock}",  RED,   "🚨"),
        ]),
        html.Div(style={'display': 'flex', 'gap': '4px', 'marginBottom': '8px'}, children=[
            html.Div(style={**CARD_STYLE, 'flex': '1', 'margin': '4px'}, children=[dcc.Graph(figure=fig_inventory_pie)]),
            html.Div(style={**CARD_STYLE, 'flex': '2', 'margin': '4px'}, children=[dcc.Graph(figure=fig_inventory_bar)]),
        ]),
        html.Div(style=CARD_STYLE, children=[
            html.H4("🚨 Critical Items Needing Immediate Reorder", style={'color': RED, 'margin': '0 0 12px 0'}),
            dash_table.DataTable(
                data=critical_df.to_dict('records'),
                columns=[{'name': c, 'id': c} for c in df_inventory_detail.columns],
                style_table={'overflowX': 'auto'},
                style_cell={'backgroundColor': DARK, 'color': WHITE,
                            'border': '1px solid #334155', 'fontSize': '12px', 'padding': '8px'},
                style_header={'backgroundColor': NAVY, 'color': BLUE, 'fontWeight': 'bold'},
                style_data_conditional=[{
                    'if': {'filter_query': '{STOCK_STATUS} = "OUT_OF_STOCK"'},
                    'backgroundColor': '#450a0a', 'color': RED
                }]
            )
        ])
    ])

# ══════════════════════════════════════════════
# PAGE 4 — FORECAST
# ══════════════════════════════════════════════
def page_forecast():
    df_forecast = query("""
        SELECT PRODUCT_ID,
               AVG(TOTAL_UNITS_SOLD) AS AVG_DEMAND,
               MAX(TOTAL_UNITS_SOLD) AS MAX_DEMAND,
               MIN(TOTAL_UNITS_SOLD) AS MIN_DEMAND
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

    fig_forecast = apply_style(px.bar(
        df_forecast, x='PRODUCT_ID', y='AVG_DEMAND',
        title='Average Demand by Product',
        **chart_style)) if len(df_forecast) > 0 else go.Figure()

    fig_spikes = apply_style(px.bar(
        df_spikes, x='PRODUCT_ID', y='SPIKE_COUNT',
        title='Demand Spikes by Product',
        color='SPIKE_COUNT',
        **chart_style)) if len(df_spikes) > 0 else go.Figure()

    return html.Div([
        html.H2("🔮 Demand Forecast Dashboard", style={'color': WHITE, 'margin': '0 0 4px 0'}),
        html.P("For Demand Planner — Forecasts, spikes, and rolling demand", style={'color': GRAY, 'margin': '0 0 20px 0', 'fontSize': '13px'}),
        html.Div(style={'display': 'flex', 'gap': '4px', 'marginBottom': '16px'}, children=[
            kpi_card("Total SKUs",     "200 Products",  BLUE,   "🛍️"),
            kpi_card("Total Stores",   "50 Stores",     GREEN,  "🏪"),
            kpi_card("Forecasts Made", "6,870",         TEAL,   "🔮"),
            kpi_card("Model",          "XGBoost",       PURPLE, "🤖"),
        ]),
        html.Div(style={'display': 'flex', 'gap': '4px', 'marginBottom': '8px'}, children=[
            html.Div(style={**CARD_STYLE, 'flex': '1', 'margin': '4px'}, children=[dcc.Graph(figure=fig_forecast)]),
            html.Div(style={**CARD_STYLE, 'flex': '1', 'margin': '4px'}, children=[dcc.Graph(figure=fig_spikes)]),
        ]),
        html.Div(style={'display': 'flex', 'gap': '4px'}, children=[
            html.Div(style={**CARD_STYLE, 'flex': '1', 'margin': '4px'}, children=[dcc.Graph(figure=fig_units)]),
            html.Div(style={**CARD_STYLE, 'flex': '1', 'margin': '4px'}, children=[dcc.Graph(figure=fig_elasticity)]),
        ]),
    ])

# ══════════════════════════════════════════════
# PAGE 5 — SUPPLY CHAIN
# ══════════════════════════════════════════════
def page_supply():
    return html.Div([
        html.H2("🚚 Supply Chain Dashboard", style={'color': WHITE, 'margin': '0 0 4px 0'}),
        html.P("For Supply Chain Manager — Risk, procurement, and logistics", style={'color': GRAY, 'margin': '0 0 20px 0', 'fontSize': '13px'}),
        html.Div(style={'display': 'flex', 'gap': '4px', 'marginBottom': '16px'}, children=[
            kpi_card("Warehouses",    "15",    BLUE,  "🏭"),
            kpi_card("Reorder Items", "707",   RED,   "📦"),
            kpi_card("Transfer Routes","15",   AMBER, "🚚"),
            kpi_card("Supply Risks",  "4,318", RED,   "⚠️"),
        ]),
        html.Div(style={'display': 'flex', 'gap': '4px', 'marginBottom': '8px'}, children=[
            html.Div(style={**CARD_STYLE, 'flex': '1', 'margin': '4px'}, children=[dcc.Graph(figure=fig_inventory_pie)]),
            html.Div(style={**CARD_STYLE, 'flex': '2', 'margin': '4px'}, children=[dcc.Graph(figure=fig_inventory_bar)]),
        ]),
        html.Div(style={'display': 'flex', 'gap': '4px'}, children=[
            html.Div(style={**CARD_STYLE, 'flex': '1', 'margin': '4px'}, children=[dcc.Graph(figure=fig_weather)]),
            html.Div(style={**CARD_STYLE, 'flex': '1', 'margin': '4px'}, children=[dcc.Graph(figure=fig_supplier_cost)]),
        ]),
    ])

# ══════════════════════════════════════════════
# PAGE 6 — SUPPLIERS
# ══════════════════════════════════════════════
def page_suppliers():
    high_tier = len(df_suppliers[df_suppliers['RELIABILITY_TIER'] == 'HIGH']) if len(df_suppliers) > 0 else 0
    total_batches = int(df_suppliers['TOTAL_BATCHES'].sum()) if len(df_suppliers) > 0 else 0

    return html.Div([
        html.H2("🏭 Supplier Analytics Dashboard", style={'color': WHITE, 'margin': '0 0 4px 0'}),
        html.P("For Procurement Team — Reliability, cost, and performance", style={'color': GRAY, 'margin': '0 0 20px 0', 'fontSize': '13px'}),
        html.Div(style={'display': 'flex', 'gap': '4px', 'marginBottom': '16px'}, children=[
            kpi_card("Total Suppliers", "30",              BLUE,   "🏭"),
            kpi_card("Top Supplier",    top_supplier[:12], GREEN,  "⭐"),
            kpi_card("HIGH Tier",       f"{high_tier}",    TEAL,   "✅"),
            kpi_card("Total Batches",   f"{total_batches:,}", AMBER, "📦"),
        ]),
        html.Div(style={**CARD_STYLE, 'marginBottom': '8px'}, children=[
            dcc.Graph(figure=fig_suppliers_bar, style={'height': '300px'})
        ]),
        html.Div(style={'display': 'flex', 'gap': '4px'}, children=[
            html.Div(style={**CARD_STYLE, 'flex': '1', 'margin': '4px'}, children=[dcc.Graph(figure=fig_supplier_cost)]),
            html.Div(style={**CARD_STYLE, 'flex': '1', 'margin': '4px'}, children=[
                html.H4("Supplier Scorecard", style={'color': WHITE, 'margin': '0 0 12px 0'}),
                dash_table.DataTable(
                    data=df_suppliers.round(3).to_dict('records'),
                    columns=[{'name': c, 'id': c} for c in
                             ['SUPPLIER_NAME', 'RELIABILITY_SCORE', 'RELIABILITY_TIER',
                              'TOTAL_BATCHES', 'AVG_UNIT_COST']],
                    style_table={'overflowX': 'auto'},
                    style_cell={'backgroundColor': DARK, 'color': WHITE,
                                'border': '1px solid #334155', 'fontSize': '11px',
                                'textAlign': 'left', 'padding': '6px'},
                    style_header={'backgroundColor': NAVY, 'color': BLUE, 'fontWeight': 'bold'},
                )
            ]),
        ]),
    ])

# ══════════════════════════════════════════════
# PAGE 7 — CUSTOMERS
# ══════════════════════════════════════════════
def page_customers():
    avg_loyalty     = float(df_customers['AVG_POINTS'].mean()) if len(df_customers) > 0 else 0
    total_customers = int(df_customers['COUNT'].sum()) if len(df_customers) > 0 else 0
    champions       = int(df_customers[df_customers['LOYALTY_TIER'] == 'GOLD']['COUNT'].sum()) if len(df_customers) > 0 else 0

    fig_session = apply_style(px.bar(
        df_customers, x='LOYALTY_TIER', y='AVG_SESSION',
        color='LOYALTY_TIER', title='Avg App Session Duration by Tier',
        color_discrete_map={'GOLD': '#F59E0B', 'SILVER': '#94A3B8', 'BRONZE': '#B45309'},
        **chart_style)) if len(df_customers) > 0 else go.Figure()

    fig_loyalty_pts = apply_style(px.bar(
        df_customers, x='LOYALTY_TIER', y='AVG_POINTS',
        color='LOYALTY_TIER', title='Avg Loyalty Points by Tier',
        color_discrete_map={'GOLD': '#F59E0B', 'SILVER': '#94A3B8', 'BRONZE': '#B45309'},
        **chart_style)) if len(df_customers) > 0 else go.Figure()

    return html.Div([
        html.H2("👥 Customer Dashboard", style={'color': WHITE, 'margin': '0 0 4px 0'}),
        html.P("For Marketing Team — Segments, loyalty, and campaigns", style={'color': GRAY, 'margin': '0 0 20px 0', 'fontSize': '13px'}),
        html.Div(style={'display': 'flex', 'gap': '4px', 'marginBottom': '16px'}, children=[
            kpi_card("Total Customers", f"{total_customers:,}", BLUE,   "👥"),
            kpi_card("Avg Loyalty Pts", f"{avg_loyalty:,.0f}", AMBER,  "⭐"),
            kpi_card("Champions",       f"{champions}",         GREEN,  "🏆"),
            kpi_card("Campaigns Active","4",                    PURPLE, "📢"),
        ]),
        html.Div(style={'display': 'flex', 'gap': '4px', 'marginBottom': '8px'}, children=[
            html.Div(style={**CARD_STYLE, 'flex': '1', 'margin': '4px'}, children=[dcc.Graph(figure=fig_customers)]),
            html.Div(style={**CARD_STYLE, 'flex': '1', 'margin': '4px'}, children=[dcc.Graph(figure=fig_loyalty_pts)]),
        ]),
        html.Div(style={'display': 'flex', 'gap': '4px'}, children=[
            html.Div(style={**CARD_STYLE, 'flex': '1', 'margin': '4px'}, children=[dcc.Graph(figure=fig_session)]),
            html.Div(style={**CARD_STYLE, 'flex': '1', 'margin': '4px'}, children=[
                html.H4("Active Campaigns", style={'color': WHITE, 'margin': '0 0 12px 0'}),
                html.Div([
                    html.Div(style={'backgroundColor': '#451a03', 'borderRadius': '8px',
                                    'padding': '12px', 'marginBottom': '8px',
                                    'border': f'1px solid {AMBER}'}, children=[
                        html.P("🏆 GOLD — VIP Early Access",
                               style={'color': AMBER, 'margin': '0', 'fontWeight': 'bold'}),
                        html.P("570 customers | Email + Push + SMS",
                               style={'color': GRAY, 'margin': '4px 0 0 0', 'fontSize': '12px'})
                    ]),
                    html.Div(style={'backgroundColor': '#1e293b', 'borderRadius': '8px',
                                    'padding': '12px', 'marginBottom': '8px',
                                    'border': '1px solid #94A3B8'}, children=[
                        html.P("🥈 SILVER — Double Points Event",
                               style={'color': '#94A3B8', 'margin': '0', 'fontWeight': 'bold'}),
                        html.P("185 customers | Email + Push",
                               style={'color': GRAY, 'margin': '4px 0 0 0', 'fontSize': '12px'})
                    ]),
                    html.Div(style={'backgroundColor': '#1c0a00', 'borderRadius': '8px',
                                    'padding': '12px', 'marginBottom': '8px',
                                    'border': '1px solid #B45309'}, children=[
                        html.P("🥉 BRONZE — Welcome Discount",
                               style={'color': '#B45309', 'margin': '0', 'fontWeight': 'bold'}),
                        html.P("245 customers | Email",
                               style={'color': GRAY, 'margin': '4px 0 0 0', 'fontSize': '12px'})
                    ]),
                    html.Div(style={'backgroundColor': '#052e16', 'borderRadius': '8px',
                                    'padding': '12px',
                                    'border': f'1px solid {GREEN}'}, children=[
                        html.P("🌟 ALL — Holiday Special",
                               style={'color': GREEN, 'margin': '0', 'fontWeight': 'bold'}),
                        html.P("1,000 customers | Email + Push + Social",
                               style={'color': GRAY, 'margin': '4px 0 0 0', 'fontSize': '12px'})
                    ]),
                ])
            ]),
        ]),
    ])

# ══════════════════════════════════════════════
# PAGE 8 — ALERTS
# ══════════════════════════════════════════════
def page_alerts():
    return html.Div([
        html.H2("🚨 Real-Time Alerts Dashboard", style={'color': WHITE, 'margin': '0 0 4px 0'}),
        html.P("For Operations Team — Fraud, anomalies, and critical alerts", style={'color': GRAY, 'margin': '0 0 20px 0', 'fontSize': '13px'}),
        html.Div(style={'display': 'flex', 'gap': '4px', 'marginBottom': '16px'}, children=[
            kpi_card("Fraud Alerts",   f"{fraud_count}", RED,   "🚨"),
            kpi_card("Out of Stock",   f"{out_of_stock}", RED,  "📦"),
            kpi_card("Supply Risks",   "4,318",          AMBER, "⚠️"),
            kpi_card("Anomalies",      "500",            AMBER, "🔍"),
        ]),
        html.Div(style={'display': 'flex', 'gap': '4px', 'marginBottom': '8px'}, children=[
            html.Div(style={**CARD_STYLE, 'flex': '1', 'margin': '4px'}, children=[dcc.Graph(figure=fig_fraud)]),
            html.Div(style={**CARD_STYLE, 'flex': '1', 'margin': '4px'}, children=[
                html.H4("🚨 Active System Alerts", style={'color': RED, 'margin': '0 0 12px 0'}),
                html.Div([
                    html.Div(style={'backgroundColor': '#450a0a', 'borderRadius': '8px',
                                    'padding': '12px', 'marginBottom': '8px',
                                    'border': f'1px solid {RED}'}, children=[
                        html.P(f"🚨 {out_of_stock} Products OUT OF STOCK",
                               style={'color': RED, 'margin': '0', 'fontWeight': 'bold'}),
                        html.P("Immediate reorder required — Auto POs created",
                               style={'color': GRAY, 'margin': '4px 0 0 0', 'fontSize': '12px'})
                    ]),
                    html.Div(style={'backgroundColor': '#431407', 'borderRadius': '8px',
                                    'padding': '12px', 'marginBottom': '8px',
                                    'border': f'1px solid {AMBER}'}, children=[
                        html.P(f"⚠️ {fraud_count} High-Risk Fraud Transactions",
                               style={'color': AMBER, 'margin': '0', 'fontWeight': 'bold'}),
                        html.P("Review flagged transactions immediately",
                               style={'color': GRAY, 'margin': '4px 0 0 0', 'fontSize': '12px'})
                    ]),
                    html.Div(style={'backgroundColor': '#1c1917', 'borderRadius': '8px',
                                    'padding': '12px', 'marginBottom': '8px',
                                    'border': '1px solid #475569'}, children=[
                        html.P("⚠️ 1,687 Critical Supply Chain Risks",
                               style={'color': AMBER, 'margin': '0', 'fontWeight': 'bold'}),
                        html.P("Activate backup suppliers immediately",
                               style={'color': GRAY, 'margin': '4px 0 0 0', 'fontSize': '12px'})
                    ]),
                    html.Div(style={'backgroundColor': '#052e16', 'borderRadius': '8px',
                                    'padding': '12px', 'marginBottom': '8px',
                                    'border': f'1px solid {GREEN}'}, children=[
                        html.P("✅ All 20 AI Agents Running",
                               style={'color': GREEN, 'margin': '0', 'fontWeight': 'bold'}),
                        html.P("System operating normally",
                               style={'color': GRAY, 'margin': '4px 0 0 0', 'fontSize': '12px'})
                    ]),
                    html.Div(style={'backgroundColor': '#0c1a2e', 'borderRadius': '8px',
                                    'padding': '12px',
                                    'border': f'1px solid {BLUE}'}, children=[
                        html.P("ℹ️ Digital Twin: Festival Season = $9,904 revenue",
                               style={'color': BLUE, 'margin': '0', 'fontWeight': 'bold'}),
                        html.P("Simulation recommends stocking up for festivals",
                               style={'color': GRAY, 'margin': '4px 0 0 0', 'fontSize': '12px'})
                    ]),
                ])
            ]),
        ]),
        html.Div(style=CARD_STYLE, children=[
            html.H4("High-Risk Fraud Transactions", style={'color': RED, 'margin': '0 0 12px 0'}),
            dash_table.DataTable(
                data=df_fraud.round(3).to_dict('records'),
                columns=[{'name': c, 'id': c} for c in df_fraud.columns],
                style_table={'overflowX': 'auto'},
                style_cell={'backgroundColor': DARK, 'color': WHITE,
                            'border': '1px solid #334155', 'fontSize': '11px', 'padding': '6px'},
                style_header={'backgroundColor': '#450a0a', 'color': RED, 'fontWeight': 'bold'},
            )
        ])
    ])

# ══════════════════════════════════════════════
# MAIN LAYOUT
# ══════════════════════════════════════════════
app.layout = html.Div(style=PAGE_STYLE, children=[
    dcc.Location(id='url', refresh=False),
    sidebar(),
    html.Div(id='page-content', style={
        'marginLeft': '210px',
        'padding': '30px',
        'minHeight': '100vh'
    })
])

@app.callback(Output('page-content', 'children'), Input('url', 'pathname'))
def display_page(pathname):
    if pathname == '/sales':
        return page_sales()
    elif pathname == '/inventory':
        return page_inventory()
    elif pathname == '/forecast':
        return page_forecast()
    elif pathname == '/supply':
        return page_supply()
    elif pathname == '/suppliers':
        return page_suppliers()
    elif pathname == '/customers':
        return page_customers()
    elif pathname == '/alerts':
        return page_alerts()
    else:
        return page_executive()

if __name__ == '__main__':
    app.run(debug=True, port=8050)