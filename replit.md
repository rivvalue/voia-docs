# Voice of Client Agent

## Overview
The Voice of Client Agent (Voxa) is a Flask-based system designed for comprehensive customer feedback collection and AI-powered analysis, specializing in Net Promoter Score (NPS) surveys. Its primary purpose is to transform raw customer feedback into actionable insights, identifying sentiment, key themes, churn risk, and growth opportunities. Voxa aims to provide businesses, specifically Rivvalue Inc., with a powerful tool for understanding customer sentiment, improving services, and fostering organic growth by leveraging AI for deeper analysis of customer interactions.

## User Preferences
Preferred communication style: Simple, everyday language.
User interface tone: Thought leadership and research-oriented language, avoiding sales-oriented messaging.
Project customization: Rivvalue Inc. branding and conversational AI surveys for enhanced user experience.

## System Architecture
The system is a Flask web application utilizing a multi-tiered architecture. The frontend uses Jinja2 templates, Bootstrap 5 (dark theme), custom CSS, and vanilla JavaScript for dynamic elements and Chart.js for data visualization. The backend is built with Flask and SQLAlchemy ORM, designed to be scalable from SQLite (development) to PostgreSQL (production). AI integration is central, primarily leveraging OpenAI API for natural language processing, sentiment analysis, and conversational survey capabilities (Voxa). TextBlob is used for additional text analysis.

## Recent Changes (September 2025)
✅ **Professional Completion Experience Implementation** - Completely replaced all JavaScript alert popups with sophisticated completion screens in both traditional and conversational surveys. Added comprehensive "What's Next?" sections offering users choice to "Try Another Session" or "Contact Rivvalue" for full Voice of Client Agent service implementation. Integrated pre-filled email contact system with professional inquiry templates. Enhanced user experience with thought leadership messaging throughout completion flow.

✅ **Cross-Survey Type Promotion** - Traditional survey completion now promotes conversational survey option and vice versa, encouraging users to experience both demonstration interfaces. Maintains consistent "Voxa Intelligence" branding while positioning current platform as research demonstration.

✅ **Validation Error UI Enhancement** - Replaced all validation alert popups with temporary, styled UI elements that appear within forms for 4 seconds. Professional error handling without interrupting user experience flow.

✅ **Production Database Integration Fixed** - Resolved dashboard data loading issue where NPS by Company table showed "No company data available". The system now correctly accesses production PostgreSQL database (Neon) with 11 actual customer responses from 9 companies. Server-side rendering implemented to prevent JavaScript interference with data display. Dashboard now shows authentic customer feedback data including company-specific NPS scores, risk levels, and response counts.

✅ **Clone Deployment Preparation** - Created comprehensive deployment guide (CLONE_DEPLOYMENT_GUIDE.md), automated deployment script (deploy.py), and full development roadmap (FULL_VOC_ROADMAP.md) to support cloning current platform for full Voice of Client Agent development while maintaining original as demonstration system. Includes environment configuration templates and production deployment instructions.

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