# Overview
The Voice of Client (VOÏA) is a Flask-based system for comprehensive customer feedback collection and AI-powered analysis, specializing in Net Promoter Score (NPS) surveys. Its primary purpose is to transform raw customer feedback into actionable insights, identifying sentiment, key themes, churn risk, and growth opportunities. VOÏA aims to provide businesses, specifically Rivvalue Inc., with a powerful tool for understanding customer sentiment, improving services, and fostering organic growth by leveraging AI for deeper analysis of customer interactions. The project is currently transitioning to a multi-tenant participant management system to support a wider range of business accounts and campaigns.

# User Preferences
Preferred communication style: Simple, everyday language.
User interface tone: Thought leadership and research-oriented language, avoiding sales-oriented messaging.
Project customization: Rivvalue Inc. branding and conversational AI surveys for enhanced user experience.

# System Architecture
The system is a Flask web application utilizing a multi-tiered architecture. The frontend uses Jinja2 templates, Bootstrap 5 (dark theme), custom CSS, vanilla JavaScript, and Chart.js for data visualization. The backend is built with Flask and SQLAlchemy ORM, designed to be scalable from SQLite to PostgreSQL. AI integration is central, primarily leveraging OpenAI API for natural language processing, sentiment analysis, and conversational survey capabilities (VOÏA), with TextBlob for additional text analysis.

Key architectural decisions include:
- **UI/UX**: Multi-step survey forms, interactive dashboards, chat-style interface for conversational surveys. Branding includes Rivvalue Inc. logo, a professional blue color scheme, and specific taglines.
- **Technical Implementations**:
    - **Survey Collection**: Multi-step forms, dynamic follow-up questions, real-time validation.
    - **AI Analysis Engine**: Sentiment analysis, key theme extraction, churn risk assessment (Minimal, Low, Medium, High), and growth opportunity identification, including NPS-based growth factor analysis.
    - **Conversational Surveys**: AI-powered (GPT-4o) natural language interface, dynamic question generation, real-time processing, structured data extraction.
    - **Data Management**: Centralized data aggregation, NPS calculation, time-based filtering, database query optimization.
    - **Authentication**: JWT token-based authentication with email validation and admin roles, server-side token generation, and automatic token invalidation after survey completion.
    - **Performance**: PostgreSQL migration, database indexing, connection pooling, asynchronous background tasks for AI analysis, and IP-based rate limiting.
- **Security**: Token-based authentication, duplicate response prevention, enhanced rate limiting, and robust input validation.
- **Branding**: "VOÏA - Voice Of Client" branding with "AI Powered Client Insights" subtitle and "VOÏA: Hear what matters. Act on what counts." tagline.
- **Multi-Tenant Architecture**: Implementation of Business Accounts, Campaigns, and Participants. This involves a new database schema for multi-tenant isolation, dual authentication for public and business access, a token system for participant survey access, and a lightweight scheduler for campaign lifecycle automation. All queries are scoped by `business_account_id` for tenant isolation.

# External Dependencies
- **OpenAI API**: For advanced AI functionalities including sentiment analysis, theme extraction, and the conversational survey system (VOÏA).
- **Bootstrap CDN**: For responsive UI components and styling.
- **Chart.js CDN**: For interactive data visualizations on the dashboard.
- **Font Awesome CDN**: For iconography.
- **Python Packages**: Flask, SQLAlchemy, OpenAI client library, TextBlob.