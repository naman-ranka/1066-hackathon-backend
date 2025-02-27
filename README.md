# Bill Split Backend

A sophisticated Django-based backend system for managing and analyzing shared expenses, featuring OCR-powered receipt scanning, real-time analytics, and intelligent bill splitting.

## 🚀 Features

### 📊 Advanced Analytics Dashboard
- Interactive spending visualizations using Plotly
- Monthly, weekly, and yearly spending trends
- Top spending categories and items
- Personal balance overview
- Group expense tracking

### 🧾 Smart Receipt Processing
- OCR-powered receipt scanning using multiple engines (Google Cloud Vision & OpenAI)
- Intelligent text parsing and data extraction
- Automatic item categorization
- Support for various receipt formats

### 💰 Bill Management
- Detailed bill tracking and storage
- Multiple participants handling
- Flexible item split options
- Tax and additional charges management
- Real-time balance calculations

### ⚙️ Task Management System
- Built-in project task tracking
- Support for various task types:
  - OCR Script Development
  - API Endpoint Creation
  - Frontend UI Development
  - Database Model Creation
  - Authentication Implementation
  - LLM Prompt Tuning

## 🛠️ Technology Stack

- **Backend Framework**: Django + Django REST Framework
- **Database**: SQLite3 (easily configurable for other databases)
- **API**: RESTful architecture
- **Data Visualization**: Plotly
- **Machine Learning**: 
  - Google Cloud Vision API
  - OpenAI API
- **CORS**: Enabled for frontend integration

## 📦 Project Structure

```
billSplitBackend/
├── bills/                  # Core bill management app
├── dashboards/            # Analytics and visualization
├── llm/                   # OCR and ML processing
├── tasks/                 # Project management
└── test_images/          # Test receipt images
```

## 🚀 Getting Started

1. Clone the repository
2. Install dependencies:
```bash
pip install -r bills/requirements.txt
```

3. Set up environment variables:
- Create a `.env` file in the root directory
- Add necessary API keys:
  ```
  OPENAI_API_KEY=your_openai_key
  GOOGLE_CLOUD_API_KEY=your_google_cloud_key
  ```

4. Run migrations:
```bash
python manage.py migrate
```

5. Start the development server:
```bash
python manage.py runserver
```

## 🔗 API Endpoints

- `/api/bills/` - Bill management endpoints
- `/api/process-receipt/` - OCR receipt processing
- `/api/tasks/` - Task management
- `/dashboard/` - Analytics dashboard
- `/` - Home page with balance overview

## 💡 Future Enhancements

- Add user authentication and authorization
- Implement real-time notifications
- Add support for multiple currencies
- Enhance OCR accuracy with ML model fine-tuning
- Add export functionality for financial reports

## 👨‍💻 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## 📝 License

This project is licensed under the MIT License - see the LICENSE file for details.