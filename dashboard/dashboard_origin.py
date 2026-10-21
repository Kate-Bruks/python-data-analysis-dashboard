import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from dash import Dash, html, dcc, Input, Output
import re
from plotly.subplots import make_subplots

# --- 1. DATEN LADEN UND VORBEREITEN ---
deals = pd.read_csv('Deals_Final.csv')
calls = pd.read_csv('Calls_Final.csv')
spend = pd.read_csv('Spend_Final.csv')
contacts = pd.read_csv('Contacts_Final.csv')

# Datumsformatierung
deals['Month'] = pd.to_datetime(deals['Created Time']).dt.to_period('M').astype(str)
calls['Month'] = pd.to_datetime(calls['Call Start Time']).dt.to_period('M').astype(str)

# Anzahl nach Monaten berechnen
deals_count = deals.groupby('Month').size().reset_index(name='Deals')
calls_count = calls.groupby('Month').size().reset_index(name='Calls')

# Trend-Tabelle erstellen
data = pd.merge(deals_count, calls_count, on='Month', how='outer').fillna(0)
data = data.sort_values('Month')

# KPI Berechnungen
total_rev_all = deals['Initial Amount Paid'].sum()
total_success_deals = deals['Successful Deal'].sum()
avg_check_all = deals['Initial Amount Paid'].mean()


# --- 2. DIAGRAMMERSTELLUNG ---

# 1. Trenddiagramm (fig)
fig = go.Figure()
fig.add_trace(go.Scatter(
    x=data['Month'], 
    y=data['Deals'], 
    name='Deals', 
    mode='lines+markers', 
    line=dict(color='#10B981', width=3)
))
fig.add_trace(go.Scatter(
    x=data['Month'], 
    y=data['Calls'], 
    name='Anrufe', 
    mode='lines+markers', 
    line=dict(color='#8B5CF6', width=3)
))
fig.update_layout(
    template='plotly_white', 
    margin=dict(t=30, b=30, l=30, r=30), 
    hovermode="x unified",
    height=350
)

# 2. Städte (fig_city)
city_data = deals.dropna(subset=['City']).copy()
city_data = city_data[city_data['City'] != 'Unknown'] 

city_analysis = city_data.groupby('City').agg(
    Revenue=('Initial Amount Paid', 'sum')
).reset_index()

top_cities = city_analysis.sort_values('Revenue', ascending=True).tail(10)

fig_city = px.bar(
    top_cities, 
    x='Revenue', 
    y='City', 
    orientation='h',
    text='Revenue',
    color='Revenue',
    color_continuous_scale='GnBu',
    labels={'Revenue': 'Umsatz (€)', 'City': 'Stadt'}
)

fig_city.update_traces(
    texttemplate='%{text:,.0f} €',
    textposition='outside',
    marker_line_color='rgb(224, 224, 224)',
    marker_line_width=1,
    hovertemplate="<b>%{y}</b><br>Umsatz: %{x:,.0f} €<extra></extra>"
)

fig_city.update_layout(
    title={'text': "<b>VERKAUFSGEOGRAFIE: TOP 10 STÄDTE NACH UMSATZ</b>", 'x': 0.02, 'font': {'size': 16, 'color': '#1a1a1a'}},
    xaxis=dict(showgrid=True, gridcolor='rgba(224, 224, 224, 0.3)', gridwidth=1, zeroline=False),
    yaxis=dict(categoryorder='total ascending', tickfont=dict(size=12)),
    plot_bgcolor='white',
    paper_bgcolor='white',
    coloraxis_showscale=False,
    height=400,
    margin=dict(l=100, r=80, t=60, b=40)
)

# 3. Produkte (fig_prod)
prod_data = deals[deals['Initial Amount Paid'] > 0].copy()
prod_data = prod_data.groupby('Product')['Initial Amount Paid'].sum().sort_values(ascending=False).reset_index()

total_revenue_prod = prod_data['Initial Amount Paid'].sum()
threshold = total_revenue_prod * 0.02

main_prods = prod_data[prod_data['Initial Amount Paid'] >= threshold].copy()
others_val = prod_data[prod_data['Initial Amount Paid'] < threshold]['Initial Amount Paid'].sum()

if others_val > 0:
    others_row = pd.DataFrame({'Product': ['Andere'], 'Initial Amount Paid': [others_val]})
    plot_data = pd.concat([main_prods, others_row], ignore_index=True)
else:
    plot_data = main_prods

fig_prod = go.Figure(data=[go.Pie(
    labels=plot_data['Product'],
    values=plot_data['Initial Amount Paid'],
    hole=0.6,
    pull=[0.05] + [0] * (len(plot_data) - 1),
    marker=dict(colors=px.colors.sequential.Mint[::-1], line=dict(color='#ffffff', width=2)),
    textinfo='percent+label',
    hoverinfo='label+value+percent',
    hovertemplate="<b>%{label}</b><br>Umsatz: %{value:,.0f} €<br>Anteil: %{percent}<extra></extra>"
)])

fig_prod.update_layout(
    title=dict(text='<b>PRODUKTANTEIL AM UMSATZ</b>', x=0.5, font_size=16),
    annotations=[dict(
        text=f'GESAMT<br><b>{int(total_revenue_prod):,} €</b>', 
        x=0.5, y=0.5, 
        font_size=13, 
        showarrow=False,
        font_color='#2c3e50'
    )],
    height=400,
    template='plotly_white',
    showlegend=True,
    legend=dict(orientation="h", yanchor="bottom", y=-0.25, xanchor="center", x=0.5),
    margin=dict(t=60, b=60, l=20, r=20)
)

# 4. Kampagnen (fig_campaign)
deals['Campaign_Clean'] = deals['Campaign'].astype(str).str.lower().str.strip()
spend['Campaign_Clean'] = spend['Campaign_Name'].astype(str).str.lower().str.strip()

deals_stats = deals.groupby('Campaign_Clean').agg(
    Unique_Leads=('Contact Name', 'nunique'),
    Success_Sales=('Successful Deal', 'sum')
).reset_index()

spend_stats = spend.groupby('Campaign_Clean').agg(
    Total_Spend=('Spend', 'sum')
).reset_index()

merged_df = pd.merge(deals_stats, spend_stats, on='Campaign_Clean', how='inner')
merged_df['CPL'] = merged_df['Total_Spend'] / merged_df['Unique_Leads']
merged_df['Conversion_Rate'] = (merged_df['Success_Sales'] / merged_df['Unique_Leads'] * 100).round(2)
merged_df['Display_Name'] = merged_df['Campaign_Clean'].str.replace('_', ' ').str.title()
plot_df = merged_df.sort_values(by='Unique_Leads', ascending=False).head(10)

fig_campaign = make_subplots(specs=[[{"secondary_y": True}]])
fig_campaign.add_trace(
    go.Bar(
        x=plot_df['Display_Name'],
        y=plot_df['Unique_Leads'],
        name="Leads (Eindeutig)",
        marker_color='#3B82F6',
        opacity=0.6,
        hovertemplate="Kampagne: %{x}<br>Leads: %{y}<extra></extra>"
    ),
    secondary_y=False,
)
fig_campaign.add_trace(
    go.Scatter(
        x=plot_df['Display_Name'],
        y=plot_df['Conversion_Rate'],
        name="Konversion (%)",
        mode="lines+markers+text",
        line=dict(color='#10B981', width=3),
        marker=dict(size=8),
        text=plot_df['Conversion_Rate'].apply(lambda x: f"{x}%"),
        textposition="top center",
        hovertemplate="Kampagne: %{x}<br>Konversion: %{y}%<extra></extra>"
    ),
    secondary_y=True,
)

fig_campaign.update_layout(
    title='<b>Effizienz TOP 10 Kampagnen: Leads vs. Konversion</b>',
    title_font_size=16,
    plot_bgcolor='white',
    hovermode="x unified",
    legend=dict(orientation="h", yanchor="bottom", y=1.05, xanchor="right", x=1),
    margin=dict(t=80, b=40, l=40, r=40),
    height=400
)
fig_campaign.update_xaxes(tickangle=35, showgrid=False)
fig_campaign.update_yaxes(title_text="Anzahl Leads", secondary_y=False, showgrid=True, gridcolor='rgba(0,0,0,0.05)')
fig_campaign.update_yaxes(title_text="Konversion (%)", secondary_y=True, showgrid=False, range=[0, plot_df['Conversion_Rate'].max() * 1.4])

# 5. Umsatz nach Kampagnen (fig_top_rev)
def clean_campaign_name(name):
    if not isinstance(name, str) or str(name).lower() == 'nan':
        return "Unbekannt"
    name = name.lower().strip()
    name = re.sub(r'\d{1,2}\.\d{1,2}\.\d{2,4}', '', name)
    name = re.sub(r'^[\s_.-]+|[\s_.-]+$', '', name)
    return name.replace('_', ' ').title()

deals['Campaign_Cleaned_Core'] = deals['Campaign'].apply(clean_campaign_name)

revenue_per_camp = deals.dropna(subset=['Campaign_Cleaned_Core']).copy()
revenue_per_camp = revenue_per_camp.groupby('Campaign_Cleaned_Core').agg(
    Revenue=('Initial Amount Paid', 'sum'),
    Sales_Count=('Successful Deal', 'sum')
).reset_index()

top_5_revenue = revenue_per_camp.sort_values(by='Revenue', ascending=True).tail(5)

fig_top_rev = px.bar(
    top_5_revenue, 
    x='Revenue', 
    y='Campaign_Cleaned_Core',
    orientation='h',
    title='<b>TOP 5 WERBEKAMPAGNEN NACH UMSATZ</b>',
    color='Revenue',
    color_continuous_scale='GnBu',
    labels={'Revenue': 'Umsatz (€)', 'Campaign_Cleaned_Core': 'Kampagnenname', 'Sales_Count': 'Deals'},
    hover_data={'Revenue': ':,.0f', 'Sales_Count': True}
)

fig_top_rev.update_traces(
    texttemplate='<b>%{x:,.0f} €</b>', 
    textposition='inside',
    insidetextanchor='end',
    marker_line_color='white',
    marker_line_width=1.5
)

fig_top_rev.update_layout(
    plot_bgcolor='white',
    title_font_size=16,
    xaxis=dict(showgrid=True, gridcolor='rgba(0,0,0,0.05)', title='Gesamtsumme (€)'),
    yaxis=dict(title=''),
    coloraxis_showscale=False,
    margin=dict(t=70, b=40, l=40, r=100),
    height=400
)

for i, row in top_5_revenue.iterrows():
    fig_top_rev.add_annotation(
        x=row['Revenue'],
        y=row['Campaign_Cleaned_Core'],
        text=f" (Deals: {int(row['Sales_Count'])})",
        showarrow=False,
        xanchor='left',
        xshift=5,
        font=dict(size=11, color='#065F46')
    )

# 6. Violin Diagramm (fig_violin)
deals_cleaned = deals.copy()
deals_cleaned['Created Time'] = pd.to_datetime(deals_cleaned['Created Time'], errors='coerce')
deals_cleaned['Closing Date'] = pd.to_datetime(deals_cleaned['Closing Date'], errors='coerce')
deals_cleaned['Duration'] = (deals_cleaned['Closing Date'] - deals_cleaned['Created Time']).dt.days
deals_cleaned = deals_cleaned.dropna(subset=['Duration'])
deals_cleaned = deals_cleaned[deals_cleaned['Duration'] >= 0]

fig_violin = px.violin(
    deals_cleaned, 
    x='Successful Deal', 
    y='Duration',
    color='Successful Deal',
    box=True,
    points="all",
    title='<b>Verteilung der Deal-Dauer (Violin Plot)</b>',
    labels={'Successful Deal': 'Deal-Status', 'Duration': 'Tage bis Abschluss'},
    color_discrete_sequence=px.colors.sequential.Viridis 
)

fig_violin.update_layout(
    plot_bgcolor='white',
    paper_bgcolor='white',
    title_font_size=16,
    xaxis=dict(
        showgrid=False,
        tickmode='array',
        tickvals=[0, 1],
        ticktext=['Fehlschlag (0)', 'Erfolg (1)']
    ),
    yaxis=dict(showgrid=True, gridcolor='rgba(0,0,0,0.1)', gridwidth=1, griddash='dash', title='Tage bis Abschluss'),
    showlegend=False,
    height=400,
    margin=dict(t=70, b=40, l=40, r=40)
)

# 7. Scatter Diagramm (fig_scatter)
fig_scatter = px.scatter(
    deals_cleaned, x='Closing Date', y='Duration', color_discrete_sequence=['#8B5CF6'], opacity=0.5,
    title='<b>DAUER NACH ABSCHLUSSDATUM</b>', labels={'Closing Date': 'Abschlussdatum', 'Duration': 'Tage'}
)
median_val = deals_cleaned['Duration'].median()
fig_scatter.add_hline(y=median_val, line_dash="dash", line_color="green", annotation_text=f"Median: {median_val:.1f} Tage")
fig_scatter.update_layout(plot_bgcolor='white', height=350, title_font_size=16)

# 8. Quellen (fig_source)
deals['Source_Clean'] = deals['Source'].astype(str).str.lower().str.strip()
source_analysis = deals.groupby('Source_Clean').agg(
    Unique_Leads=('Contact Name', 'nunique'),
    Success_Sales=('Successful Deal', 'sum')
).reset_index()

source_analysis['Conversion_Rate'] = (source_analysis['Success_Sales'] / source_analysis['Unique_Leads'] * 100).round(2)
source_analysis = source_analysis[source_analysis['Source_Clean'] != 'nan']
source_analysis = source_analysis.sort_values(by='Unique_Leads', ascending=False).head(10)

fig_source = make_subplots(specs=[[{"secondary_y": True}]])
fig_source.add_trace(go.Bar(x=source_analysis['Source_Clean'], y=source_analysis['Unique_Leads'], name="Leads", marker_color='#8B5CF6', opacity=0.6), secondary_y=False)
fig_source.add_trace(go.Scatter(
    x=source_analysis['Source_Clean'], y=source_analysis['Conversion_Rate'], name="Konversion (%)", mode="lines+markers+text",
    line=dict(color='#F59E0B', width=3), marker=dict(size=8, symbol='square'),
    text=source_analysis['Conversion_Rate'].apply(lambda x: f"{x}%"), textposition="top center"
), secondary_y=True)
fig_source.update_layout(title='<b>Effizienz der Quellen</b>', template='plotly_white', hovermode="x unified", height=400, title_font_size=16)

# 9. Netzdiagramm (fig_radar)
radar_df = deals.groupby('Payment Type').agg(
    Count=('Successful Deal', 'count'),
    CR=('Successful Deal', 'mean'),
    AvgCheck=('Initial Amount Paid', 'mean')
).reset_index()

raw_data_radar = radar_df.copy()

for col in ['Count', 'CR', 'AvgCheck']:
    if radar_df[col].max() > 0:
        radar_df[col] = radar_df[col] / radar_df[col].max()

labels_radar = ['Beliebtheit', 'Konversion', 'Durchschn. Check']
fig_radar = go.Figure()
colors_radar = ['#66c2a5', '#fc8d62', '#8da0cb'] 

for i, row in radar_df.iterrows():
    r_values = [row['Count'], row['CR'], row['AvgCheck'], row['Count']]
    theta_labels = labels_radar + [labels_radar[0]]
    
    fig_radar.add_trace(go.Scatterpolar(
        r=r_values,
        theta=theta_labels,
        fill='toself',
        name=row['Payment Type'],
        line=dict(color=colors_radar[i % len(colors_radar)]),
        hovertemplate=(
            f"<b>{row['Payment Type']}</b><br>" +
            f"Beliebtheit: {raw_data_radar.iloc[i]['Count']}<br>" +
            f"Konversion: {raw_data_radar.iloc[i]['CR']:.2%}<br>" +
            f"Durchschn. Check: {raw_data_radar.iloc[i]['AvgCheck']:.0f}€<extra></extra>"
        )
    ))

fig_radar.update_layout(
    polar=dict(
        radialaxis=dict(visible=False, range=[0, 1.1]),
        angularaxis=dict(direction="clockwise", period=3)
    ),
    title={'text': "<b>Profil der Zahlungsmethoden-Effizienz</b>", 'x': 0.5, 'xanchor': 'center', 'font': {'size': 16}},
    template="plotly_white",
    height=400,
    margin=dict(l=40, r=40, t=60, b=40)
)

# 10. Manager Analyse (fig_owners)
owner_stats = deals.groupby('Deal Owner Name').agg(
    Total_Deals=('Contact Name', 'count'),
    Success_Sales=('Successful Deal', 'sum'),
    Real_Revenue=('Initial Amount Paid', 'sum')
).reset_index()

owner_stats['CR_%'] = (owner_stats['Success_Sales'] / owner_stats['Total_Deals'] * 100).round(2)
top_5_owners = owner_stats.sort_values(by='Real_Revenue', ascending=False).head(5)

fig_owners = make_subplots(specs=[[{"secondary_y": True}]])
fig_owners.add_trace(
    go.Bar(
        x=top_5_owners['Deal Owner Name'],
        y=top_5_owners['Real_Revenue'],
        name="Umsatz (€)",
        marker_color='#10B981', 
        opacity=0.6,
        text=top_5_owners['Real_Revenue'].apply(lambda x: f"{int(x):,} €"),
        textposition='outside',
        hovertemplate="Manager: %{x}<br>Umsatz: %{y:,.0f} €<extra></extra>"
    ),
    secondary_y=False
)
fig_owners.add_trace(
    go.Scatter(
        x=top_5_owners['Deal Owner Name'],
        y=top_5_owners['CR_%'],
        name="Konversion (%)",
        mode="lines+markers+text",
        line=dict(color='#3B82F6', width=3),
        marker=dict(size=10, symbol='circle'),
        text=top_5_owners['CR_%'].apply(lambda x: f"{x}%"),
        textposition="top center",
        hovertemplate="Manager: %{x}<br>Konversion: %{y}%<extra></extra>"
    ),
    secondary_y=True
)

fig_owners.update_layout(
    title='<b>TOP 5 Manager: Umsatz vs. Konversion</b>',
    title_font_size=16,
    plot_bgcolor='white',
    hovermode="x unified",
    legend=dict(orientation="h", yanchor="bottom", y=1.05, xanchor="right", x=1),
    margin=dict(t=80, b=40, l=40, r=40),
    height=400
)
fig_owners.update_yaxes(title_text="Umsatz (€)", secondary_y=False, showgrid=True, gridcolor='rgba(0,0,0,0.1)')
fig_owners.update_yaxes(title_text="Konversion (%)", secondary_y=True, showgrid=False, range=[0, top_5_owners['CR_%'].max() * 1.4])


# --- 3. DASH LAYOUT ---
app = Dash(__name__)

app.layout = html.Div(style={
    'backgroundColor': '#f3f4f6', 
    'padding': '20px', 
    'fontFamily': 'Segoe UI, sans-serif',
    'maxWidth': '1400px', 
    'margin': '0 auto'
}, children=[
    
    html.H1("📊 Kennzahlen der Programmierschule", style={'textAlign': 'center', 'color': '#1f2937', 'marginBottom': '25px'}),

    # KPI KARTEIKARTEN
    html.Div(style={'display': 'flex', 'gap': '20px', 'marginBottom': '25px', 'justifyContent': 'center'}, children=[
        html.Div([
            html.P("Gesamtumsatz", style={'margin': '0', 'color': '#6b7280', 'fontSize': '14px'}),
            html.H2(f"{total_rev_all:,.0f} €", style={'margin': '5px 0 0 0', 'color': '#10b981', 'fontSize': '26px'})
        ], style={'backgroundColor': 'white', 'padding': '18px', 'borderRadius': '12px', 'textAlign': 'center', 'flex': '1', 'boxShadow': '0 2px 4px rgba(0,0,0,0.05)'}),
        
        html.Div([
            html.P("Erfolgreiche Deals", style={'margin': '0', 'color': '#6b7280', 'fontSize': '14px'}),
            html.H2(f"{int(total_success_deals):,}", style={'margin': '5px 0 0 0', 'color': '#3b82f6', 'fontSize': '26px'})
        ], style={'backgroundColor': 'white', 'padding': '18px', 'borderRadius': '12px', 'textAlign': 'center', 'flex': '1', 'boxShadow': '0 2px 4px rgba(0,0,0,0.05)'}),

        html.Div([
            html.P("Durchschnittlicher Check", style={'margin': '0', 'color': '#6b7280', 'fontSize': '14px'}),
            html.H2(f"{avg_check_all:,.0f} €", style={'margin': '5px 0 0 0', 'color': '#8b5cf6', 'fontSize': '26px'})
        ], style={'backgroundColor': 'white', 'padding': '18px', 'borderRadius': '12px', 'textAlign': 'center', 'flex': '1', 'boxShadow': '0 2px 4px rgba(0,0,0,0.05)'}),
    ]),

    # REITER (TABS)
    dcc.Tabs(id="tabs-styled-with-inline", value='tab-1', children=[
        dcc.Tab(label='💰 Vertrieb & Finanzen', value='tab-1', style={'padding': '12px'}, selected_style={'backgroundColor': '#3b82f6', 'color': 'white', 'padding': '12px'}),
        dcc.Tab(label='📣 Marketing & Kampagnen', value='tab-2', style={'padding': '12px'}, selected_style={'backgroundColor': '#10b981', 'color': 'white', 'padding': '12px'}),
    ]),
    
    html.Div(id='tabs-content-inline', style={'paddingTop': '20px'})
])

# --- 4. CALLBACK LOGIK ---
@app.callback(Output('tabs-content-inline', 'children'),
              Input('tabs-styled-with-inline', 'value'))
def render_content(tab):
    if tab == 'tab-1':
        return html.Div([
            # Zeile 1: Dynamik
            html.Div([
                html.H4("📈 Monatliche Entwicklung von Deals und Anrufen", style={'margin': '0 0 10px 0', 'color': '#374151'}), 
                dcc.Graph(figure=fig, config={'responsive': True})
            ], style={'backgroundColor': 'white', 'padding': '15px', 'borderRadius': '10px', 'marginBottom': '20px', 'boxShadow': '0 2px 4px rgba(0,0,0,0.02)'}),
        
            # Zeile 2: Geografie und Produkte
            html.Div(style={'display': 'flex', 'gap': '20px', 'marginBottom': '20px'}, children=[
                html.Div([dcc.Graph(figure=fig_city, config={'responsive': True})], style={'flex': '1', 'backgroundColor': 'white', 'padding': '15px', 'borderRadius': '10px', 'boxShadow': '0 2px 4px rgba(0,0,0,0.02)'}),
                html.Div([dcc.Graph(figure=fig_prod, config={'responsive': True})], style={'flex': '1', 'backgroundColor': 'white', 'padding': '15px', 'borderRadius': '10px', 'boxShadow': '0 2px 4px rgba(0,0,0,0.02)'}),
            ]),
        
            # Zeile 3: Manager und Zahlungen
            html.Div(style={'display': 'flex', 'gap': '20px'}, children=[
                html.Div([dcc.Graph(figure=fig_owners, config={'responsive': True})], style={'flex': '1', 'backgroundColor': 'white', 'padding': '15px', 'borderRadius': '10px', 'boxShadow': '0 2px 4px rgba(0,0,0,0.02)'}),
                html.Div([dcc.Graph(figure=fig_radar, config={'responsive': True})], style={'flex': '1', 'backgroundColor': 'white', 'padding': '15px', 'borderRadius': '10px', 'boxShadow': '0 2px 4px rgba(0,0,0,0.02)'}),
            ]),
        ])
    
    elif tab == 'tab-2':
        return html.Div([
            html.Div(style={'display': 'flex', 'gap': '20px', 'marginBottom': '20px'}, children=[
                html.Div([dcc.Graph(figure=fig_campaign, config={'responsive': True})], style={'flex': '1', 'backgroundColor': 'white', 'padding': '15px', 'borderRadius': '10px', 'boxShadow': '0 2px 4px rgba(0,0,0,0.02)'}),
                html.Div([dcc.Graph(figure=fig_source, config={'responsive': True})], style={'flex': '1', 'backgroundColor': 'white', 'padding': '15px', 'borderRadius': '10px', 'boxShadow': '0 2px 4px rgba(0,0,0,0.02)'}),
            ]),
            html.Div(style={'display': 'flex', 'gap': '20px', 'marginBottom': '20px'}, children=[
                html.Div([dcc.Graph(figure=fig_top_rev, config={'responsive': True})], style={'flex': '1', 'backgroundColor': 'white', 'padding': '15px', 'borderRadius': '10px', 'boxShadow': '0 2px 4px rgba(0,0,0,0.02)'}),
                html.Div([dcc.Graph(figure=fig_violin, config={'responsive': True})], style={'flex': '1', 'backgroundColor': 'white', 'padding': '15px', 'borderRadius': '10px', 'boxShadow': '0 2px 4px rgba(0,0,0,0.02)'}),
            ]),
            html.Div([dcc.Graph(figure=fig_scatter, config={'responsive': True})], style={'backgroundColor': 'white', 'padding': '15px', 'borderRadius': '10px', 'boxShadow': '0 2px 4px rgba(0,0,0,0.02)'})
        ])

if __name__ == '__main__':
    app.run(debug=True, port=8050)