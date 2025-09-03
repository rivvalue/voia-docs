# Voice of Client Agent

## Overview
The Voice of Client Agent (Voxa) is a Flask-based system designed for comprehensive customer feedback collection and AI-powered analysis, specializing in Net Promoter Score (NPS) surveys. Its primary purpose is to transform raw customer feedback into actionable insights, identifying sentiment, key themes, churn risk, and growth opportunities. Voxa aims to provide businesses, specifically Rivvalue Inc., with a powerful tool for understanding customer sentiment, improving services, and fostering organic growth by leveraging AI for deeper analysis of customer interactions.

## User Preferences
Preferred communication style: Simple, everyday language.
Project customization: Rivvalue Inc. branding and conversational AI surveys for enhanced user experience.

## System Architecture
The system is a Flask web application utilizing a multi-tiered architecture. The frontend uses Jinja2 templates, Bootstrap 5 (dark theme), custom CSS, and vanilla JavaScript for dynamic elements and Chart.js for data visualization. The backend is built with Flask and SQLAlchemy ORM, designed to be scalable from SQLite (development) to PostgreSQL (production). AI integration is central, primarily leveraging OpenAI API for natural language processing, sentiment analysis, and conversational survey capabilities (Voxa). TextBlob is used for additional text analysis.

## Recent Changes (September 2025)
✅ **Enhanced User Onboarding and Experience** - Completely redesigned landing page and Get Token page to better drive visitor engagement with Voxa as a "sneak peek" into Rivvalue's Voice of Client Agent platform. Added compelling hero section with animated elements, 3-step demo journey, prominent CTAs, and messaging emphasizing the free demo nature. Enhanced Get Token page with sneak peek badges, improved copy, and visual indicators highlighting AI conversation as the preferred choice.

✅ **JavaScript Error Fixes** - Resolved console errors in survey type selection by properly passing element context to selectSurveyType function. Fixed event handling issues that were causing "undefined is not an object" errors during card selection.

✅ **Token Invalidation System Implemented** - Automatic server-side session clearing after survey completion prevents duplicate submissions and survey restarts. Both traditional and conversational surveys now require new tokens after successful completion.

✅ **Company Name Case-Insensitive Normalization** - Fixed bug where "mondou" and "Mondou" were treated as separate companies. All company names are now normalized to Title Case on submission and analytics group companies case-insensitively using SQL UPPER() functions. Updated both NPS analytics and Growth Opportunities sections to use case-insensitive grouping.

✅ **Production Database Integration Fixed** - Resolved dashboard data loading issue where NPS by Company table showed "No company data available". The system now correctly accesses production PostgreSQL database (Neon) with 11 actual customer responses from 9 companies. Server-side rendering implemented to prevent JavaScript interference with data display. Dashboard now shows authentic customer feedback data including company-specific NPS scores, risk levels, and response counts. **CONFIRMED WORKING**: After deployment, production dashboard successfully displays all company data with proper JavaScript console logging.

Key architectural decisions include:
- **UI/UX**: Multi-step survey forms with progressive disclosure, interactive dashboards, and a chat-style interface for conversational surveys. Branding includes Rivvalue Inc. logo, a professional blue color scheme, and specific taglines.
- **Technical Implementations**:
    - **Survey Collection**: Multi-step forms, dynamic follow-up questions, real-time validation.
    - **AI Analysis Engine**: Sentiment analysis, key theme extraction, churn risk assessment (categorical levels: Minimal, Low, Medium, High), and growth opportunity identification, including NPS-based growth factor analysis.
    - **Conversational Surveys**: AI-powered (GPT-4o) natural language interface replacing traditional forms, dynamic question generation, real-time processing, and structured data extraction from natural language.
    - **Data Management**: Centralized data aggregation, NPS calculation, time-based filtering, and database query optimization.
    - **Authentication**: JWT token-based authentication with email validation and admin roles for data export protection, featuring server-side token generation for enhanced security. **Automatic token invalidation after survey completion prevents duplicate submissions.**
    - **Performance**: PostgreSQL migration, database indexing, connection pooling, asynchronous background task processing for AI analysis, and comprehensive rate limiting (IP-based).
- **Security**: Token-based authentication, duplicate response prevention (via separate submit/overwrite endpoints), enhanced rate limiting, and robust input validation.
- **Branding**: "Voxa - Voice Of Client Agent" branding with "AI Powered Client Insights" subtitle and "Voxa: Hear what matters. Act on what counts." tagline.

## External Dependencies
- **OpenAI API**: For advanced AI functionalities including sentiment analysis, theme extraction, and the conversational survey system (Voxa).
- **Bootstrap CDN**: For responsive UI components and styling.
- **Chart.js CDN**: For interactive data visualizations on the dashboard.
- **Font Awesome CDN**: For iconography.
- **Python Packages**: Flask, SQLAlchemy, OpenAI client library, TextBlob.