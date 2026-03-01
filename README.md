# Crypto Intelligence Dashboard

A minimal real-time crypto market terminal built with Python and Streamlit.

## Overview

This project is a fintech-style dashboard that allows users to:

- Track cryptocurrency prices in real-time
- Select display currency (USD, EUR, etc.)
- View dynamic interactive charts
- Access live TradingView trading charts
- Read recent news related to selected coins
- Receive AI-generated market sentiment analysis

The application focuses on clean architecture, performance, and intelligent data presentation.

---

## Tech Stack

- Python
- Streamlit
- Plotly
- CoinMarketCap API
- CoinGecko API
- News API
- OpenRouter (arcee-ai/trinity-large-preview)

---

## Features

- 3-panel dashboard layout
- Real-time price updates
- Multi-currency support
- Dynamic chart updates
- TradingView integration
- AI-driven sentiment analysis
- News-based market insights
- Cached responses for faster performance

---

## Architecture

- Left Sidebar: Coin + currency selection
- Main Area: Market data + real-time chart
- Right Sidebar: News + AI analysis
- Cached API responses
- Structured AI prompt design

---

## Quality Assurance

- **Functional Testing:** Validates multi-API data integration and verifies the accuracy of AI sentiment analysis outputs.
- **Regression Testing:** Automated workflows to ensure core dashboard stability and real-time visualization performance across iterative updates.

---

## Installation

1. Clone the repository
2. Install dependencies:
   pip install -r requirements.txt
3. Add your API keys
4. Run:
   streamlit run app.py

---

## Project Goal

To demonstrate:

- Multi-API integration
- AI-enhanced financial analysis
- Real-time data visualization
- Clean UI/UX thinking
- Production-style dashboard structure

This project is designed as a portfolio piece for fintech and data-focused roles.