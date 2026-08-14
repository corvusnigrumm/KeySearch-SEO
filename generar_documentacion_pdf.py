import os
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

pdf_filename = "KeySearch_Google_Ads_API_Documentation.pdf"

doc = SimpleDocTemplate(
    pdf_filename,
    pagesize=letter,
    rightMargin=54,
    leftMargin=54,
    topMargin=54,
    bottomMargin=54
)

styles = getSampleStyleSheet()

title_style = ParagraphStyle(
    'DocTitle',
    parent=styles['Heading1'],
    fontName='Helvetica-Bold',
    fontSize=20,
    leading=24,
    textColor=colors.HexColor('#1A73E8'),
    spaceAfter=12
)

h2_style = ParagraphStyle(
    'SectionHeader',
    parent=styles['Heading2'],
    fontName='Helvetica-Bold',
    fontSize=13,
    leading=16,
    textColor=colors.HexColor('#202124'),
    spaceBefore=10,
    spaceAfter=4
)

body_style = ParagraphStyle(
    'BodyTextCustom',
    parent=styles['Normal'],
    fontName='Helvetica',
    fontSize=10,
    leading=14,
    textColor=colors.HexColor('#3C4043'),
    spaceAfter=8
)

bullet_style = ParagraphStyle(
    'BulletCustom',
    parent=body_style,
    leftIndent=15,
    spaceAfter=3
)

story = []

# Title
story.append(Paragraph("Google Ads API Tool Design & Architecture Document", title_style))
story.append(HRFlowable(width="100%", thickness=2, color=colors.HexColor('#1A73E8'), spaceAfter=15))

# Company Name
story.append(Paragraph("<b>Company Name:</b> Corvus Nigrum / KeySearch Editorial & Ads Optimizer", h2_style))
story.append(Spacer(1, 4))

# Business Model
story.append(Paragraph("<b>Business Model:</b>", h2_style))
story.append(Paragraph(
    "Corvus Nigrum operates an internal editorial planning and digital advertising automation suite named "
    "KeySearch Editorial & Ads Optimizer. Our primary business is running a news portal and digital newspaper, "
    "where we publish daily articles on current events, politics, sports, and culture. "
    "We use the Google Ads API to automate the creation and structuring of Search Ad campaigns that promote "
    "our newly published articles to relevant audiences, driving subscriptions and qualified traffic to our portal.",
    body_style
))
story.append(Spacer(1, 4))

# Tool Access/Use
story.append(Paragraph("<b>Tool Access/Use:</b>", h2_style))
story.append(Paragraph(
    "This tool is used exclusively by internal team members: editors, content strategists, and the in-house "
    "digital marketing team. After publishing a news article, the team uses the tool to automatically generate "
    "a full Google Ads Search campaign structure (campaign name, ad groups by topic category, targeted keywords "
    "with phrase match, and Responsive Search Ad copy) which is then imported directly into our active Google Ads "
    "account via Google Ads Editor. No external third-party users or general public access this tool.",
    body_style
))
story.append(Spacer(1, 4))

# Tool Design
story.append(Paragraph("<b>Tool Design & Workflow:</b>", h2_style))
story.append(Paragraph(
    "The KeySearch Editorial & Ads Optimizer implements a fully integrated editorial-to-campaign pipeline:",
    body_style
))
story.append(Paragraph(
    "<b>Step 1 - Topic Discovery:</b> The editor enters the article topic. The tool extracts related search signals "
    "from Google Autocomplete (PAA questions, related searches) using HTTP-based scraping.",
    bullet_style
))
story.append(Paragraph(
    "<b>Step 2 - Metrics Enrichment via Google Ads API:</b> The tool calls the Google Ads API "
    "(GenerateKeywordHistoricalMetrics via KeywordPlanIdeaService) to retrieve real historical monthly search volumes, "
    "competition index, and Top of Page CPC bids for all discovered keywords. This data is essential to prioritize "
    "which keywords to target in the campaign.",
    bullet_style
))
story.append(Paragraph(
    "<b>Step 3 - AI Editorial & Ad Copy Generation:</b> The tool sends the top keywords to a Groq LLM API "
    "(Llama 3) to generate: (a) SEO-optimized article headlines, (b) Google Ads Responsive Search Ad headlines "
    "(<=30 chars) and descriptions (<=90 chars), tailored to the article topic and target country.",
    bullet_style
))
story.append(Paragraph(
    "<b>Step 4 - Campaign Structure Export:</b> The tool generates a complete Google Ads campaign structure "
    "in the official Google Ads Editor import format (Excel), including: Campaign name, Ad Groups organized by "
    "keyword category, Keywords with Phrase match type, Headline 1/2/3, Description 1/2, and Final URL pointing "
    "to the published article. This file is directly imported into the active Google Ads account.",
    bullet_style
))
story.append(Spacer(1, 4))

# API Services Called
story.append(Paragraph("<b>API Services Called:</b>", h2_style))
story.append(Paragraph("&bull; <b>KeywordPlanIdeaService (GenerateKeywordHistoricalMetrics):</b> Retrieves real historical monthly search volumes, competition level, competition index, and low/high Top of Page bid estimates for the article-related keywords.", bullet_style))
story.append(Paragraph("&bull; <b>GeoTargetConstantService (SuggestGeoTargetConstants):</b> Resolves country codes (e.g. 'CO') into Google Ads geo target resource names for geographically targeted campaigns.", bullet_style))
story.append(Paragraph("&bull; <b>GoogleAdsService (language_constant query):</b> Retrieves language resource names for precise language targeting in ad campaigns.", bullet_style))
story.append(Spacer(1, 10))

# Why Standard Access is Needed
story.append(Paragraph("<b>Why Standard/Basic Access is Required:</b>", h2_style))
story.append(Paragraph(
    "Our news portal publishes 10-20 articles daily. Each article triggers an automated pipeline that calls the "
    "Google Ads API to fetch keyword metrics for 200-500 keywords per article (one batch of GenerateKeywordHistoricalMetrics "
    "per article). At this publishing volume, we consistently hit the daily operation limits of the Test account tier. "
    "Standard access is required to support our production publishing workflow without quota interruptions.",
    body_style
))
story.append(Spacer(1, 4))

# Tool Mockups
story.append(Paragraph("<b>Tool Mockups & User Interface:</b>", h2_style))
story.append(Paragraph("Below is a structural representation of the campaign output generated by KeySearch for each published article:", body_style))
story.append(Spacer(1, 6))

# Mockup Table Header
header_data = [[Paragraph("<b><font color='#FFFFFF' size=11>KeySearch - Google Ads Campaign Export (Ads Editor Format)</font></b>", body_style)]]
t_header = Table(header_data, colWidths=[500])
t_header.setStyle(TableStyle([
    ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#1A73E8')),
    ('ALIGN', (0,0), (-1,-1), 'LEFT'),
    ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
    ('TOPPADDING', (0,0), (-1,-1), 8),
    ('BOTTOMPADDING', (0,0), (-1,-1), 8),
    ('LEFTPADDING', (0,0), (-1,-1), 12),
]))
story.append(t_header)

# Mockup Metrics Table
col_headers = [
    Paragraph("<b>Campaign</b>", body_style),
    Paragraph("<b>Ad Group</b>", body_style),
    Paragraph("<b>Keyword</b>", body_style),
    Paragraph("<b>Match Type</b>", body_style),
    Paragraph("<b>Headline 1</b>", body_style),
]
mock_row1 = [
    Paragraph("Promo_Periodico_\nnoticias_hoy", body_style),
    Paragraph("Politica - Nacional", body_style),
    Paragraph("noticias colombia hoy", body_style),
    Paragraph("Phrase", body_style),
    Paragraph("Leer Nota: Noticias", body_style),
]
mock_row2 = [
    Paragraph("Promo_Periodico_\nnoticias_hoy", body_style),
    Paragraph("Economia", body_style),
    Paragraph("economia colombia 2025", body_style),
    Paragraph("Phrase", body_style),
    Paragraph("Analisis Economico", body_style),
]
mock_data = [col_headers, mock_row1, mock_row2]
t_mock = Table(mock_data, colWidths=[100, 100, 110, 80, 110])
t_mock.setStyle(TableStyle([
    ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#E8F0FE')),
    ('BACKGROUND', (0,1), (-1,-1), colors.HexColor('#F8F9FA')),
    ('BOX', (0,0), (-1,-1), 1, colors.HexColor('#DADCE0')),
    ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor('#E8EAED')),
    ('ALIGN', (0,0), (-1,-1), 'CENTER'),
    ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
    ('TOPPADDING', (0,0), (-1,-1), 8),
    ('BOTTOMPADDING', (0,0), (-1,-1), 8),
]))
story.append(t_mock)
story.append(Spacer(1, 12))

# Closing statement
story.append(Paragraph("<b>Summary:</b>", h2_style))
story.append(Paragraph(
    "KeySearch Editorial & Ads Optimizer is not a standalone keyword research tool. It is an end-to-end "
    "editorial-to-advertising automation pipeline. The Google Ads API is the critical component that provides "
    "the real market data (search volumes, CPC, competition) required to make informed decisions about campaign "
    "budget allocation and keyword targeting before each article promotion campaign goes live in our active "
    "Google Ads account.",
    body_style
))

doc.build(story)
print("PDF creado con exito:", os.path.abspath(pdf_filename))
