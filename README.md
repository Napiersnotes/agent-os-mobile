```markdown
# 🤖 Agent OS - Mobile First AI Agent Platform

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.11](https://img.shields.io/badge/Python-3.11-blue.svg)](https://www.python.org/)
[![React](https://img.shields.io/badge/React-18-blue.svg)](https://reactjs.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.104-green.svg)](https://fastapi.tiangolo.com/)

A production-ready AI Agent Operating System with mobile-optimized web interface. Deploy your own swarm of AI agents that can process complex tasks through simple smartphone inputs.

## 🚀 Features

### 🤖 Multi-Agent Architecture
- **Planner Agent**: Breaks down complex tasks
- **Researcher Agent**: Web search and information gathering
- **Analyst Agent**: Data analysis and insights
- **Writer Agent**: Content creation and summarization
- **General Agent**: Handles miscellaneous tasks

### 📱 Mobile-First Interface
- Progressive Web App (PWA) support
- Touch-optimized controls
- Offline capability
- Real-time updates via WebSocket
- Speech-to-text input support

### 🏗️ Production Ready
- Docker & Kubernetes ready
- PostgreSQL + Redis + Vector DB
- Monitoring with Prometheus/Grafana
- API rate limiting
- Automated backups
- Health checks

### 🔒 Security Features
- JWT authentication
- Input sanitization
- Rate limiting
- Audit logging
- Sandboxed execution
- Privacy-first design

## 📋 Quick Start

### Prerequisites
- Docker & Docker Compose
- Python 3.11+
- Node.js 18+
- PostgreSQL 14+
- Redis 7+

### Option 1: Docker (Recommended)
```bash
# Clone the repository
git clone https://github.com/yourusername/agent-os.git
cd agent-os

# Copy environment file
cp .env.example .env
# Edit .env with your settings

# Start with Docker Compose
docker-compose up -d

# Access the application
# Web Interface: http://localhost:3000
# API Docs: http://localhost:8000/api/docs
# Grafana: http://localhost:3001 (admin/admin)
```

Option 2: Manual Installation

```bash
# Backend
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env file

# Initialize database
alembic upgrade head

# Start backend
uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000

# Frontend (in another terminal)
cd frontend
npm install
npm start
```

📱 Mobile Usage

PWA Installation

1. Open the web interface on your smartphone
2. Tap "Share" button
3. Select "Add to Home Screen"
4. The app will install like a native application

Features for Mobile

· Voice Input: Tap microphone icon to speak tasks
· Camera Upload: Attach photos/documents
· Offline Mode: Queue tasks when offline
· Push Notifications: Get task completion alerts
· Gesture Controls: Swipe to navigate

Example Mobile Tasks

```
📝 "Write a professional email to schedule a meeting"
🔍 "Research best practices for remote team management"
📊 "Analyze these sales numbers from the uploaded spreadsheet"
✍️ "Create a social media post for our new product launch"
📋 "Summarize this long article into key points"
```

🏗️ Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Mobile Web    │    │   FastAPI API   │    │   PostgreSQL    │
│   Interface     │◄──►│   Layer         │◄──►│   Database      │
│   (React PWA)   │    │   (Python)      │    │                 │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         │                       │                       │
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   WebSocket     │    │   Agent         │    │   Redis Cache   │
│   Real-time     │    │   Orchestrator  │    │                 │
│   Updates       │    │   (Core)        │    │                 │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         │                       │                       │
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Vector DB     │    │   External      │    │   Monitoring    │
│   (Chroma)      │    │   APIs          │    │   (Prometheus)  │
│                 │    │   (OpenAI, etc) │    │                 │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

🔧 Configuration

Environment Variables

Create a .env file in the backend directory:

```env
# Database
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/agentos
REDIS_URL=redis://localhost:6379

# Security
SECRET_KEY=your-secret-key-here
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=1440

# External APIs
OPENAI_API_KEY=your-openai-key
SERPAPI_KEY=your-serpapi-key

# Email (Optional)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASS=your-app-password

# Monitoring
PROMETHEUS_PORT=9090
GRAFANA_PORT=3001
```

Agent Configuration

Edit backend/src/config/agents.yaml:

```yaml
agents:
  planner:
    enabled: true
    model: gpt-4
    max_tokens: 1000
    
  researcher:
    enabled: true
    max_results: 5
    sources: ["web", "arxiv", "news"]
    
  analyst:
    enabled: true
    tools: ["pandas", "numpy", "statistics"]
    
  writer:
    enabled: true
    style: "professional"
    languages: ["en", "de", "fr"]
```

📊 Monitoring & Metrics

The system includes comprehensive monitoring:

· Prometheus: Collects metrics from all services
· Grafana: Dashboard for visualization
· Health Checks: Automatic service monitoring
· Performance Metrics: Response times, error rates
· Business Metrics: Tasks processed, user activity

Access dashboards:

· Grafana: http://localhost:3001 (admin/admin)
· Prometheus: http://localhost:9090

🔌 API Usage

Authentication

```bash
# Register
curl -X POST http://localhost:8000/api/register \
  -H "Content-Type: application/json" \
  -d '{"email":"user@example.com","password":"password","name":"John Doe"}'

# Login
curl -X POST http://localhost:8000/api/login \
  -H "Content-Type: application/json" \
  -d '{"email":"user@example.com","password":"password"}'

# Use token in subsequent requests
curl -H "Authorization: Bearer <token>" http://localhost:8000/api/tasks
```

Submit a Task

```python
import requests
import json

token = "your-jwt-token"
headers = {"Authorization": f"Bearer {token}"}

task = {
    "input_text": "Research renewable energy trends in 2024",
    "priority": "high",
    "metadata": {
        "category": "research",
        "deadline": "2024-12-31"
    }
}

response = requests.post(
    "http://localhost:8000/api/tasks",
    headers=headers,
    json=task
)

print(response.json())
# {"task_id": "uuid", "status": "accepted", "message": "Task submitted"}
```

WebSocket Updates

```javascript
const ws = new WebSocket(`ws://localhost:8000/ws/mobile_1?token=${token}`);

ws.onmessage = (event) => {
    const data = JSON.parse(event.data);
    if (data.type === 'task_update') {
        console.log('Task update:', data.status);
    }
};

// Subscribe to task updates
ws.send(JSON.stringify({
    type: 'subscribe_task',
    task_id: 'your-task-id'
}));
```

🧪 Testing

Run Tests

```bash
# Backend tests
cd backend
pytest tests/ -v

# Frontend tests
cd frontend
npm test

# Integration tests
docker-compose -f docker-compose.test.yml up
```

Load Testing

```bash
# Install k6
brew install k6

# Run load test
k6 run tests/load_test.js
```

📈 Deployment

AWS ECS

```bash
# Build and push Docker images
docker build -t your-ecr-repo/agent-os-backend:latest ./backend
docker push your-ecr-repo/agent-os-backend:latest

# Deploy with Terraform
cd terraform
terraform init
terraform apply
```

Kubernetes

```bash
# Apply Kubernetes manifests
kubectl apply -f k8s/namespace.yaml
kubectl apply -f k8s/configmap.yaml
kubectl apply -f k8s/secrets.yaml
kubectl apply -f k8s/deployment.yaml
kubectl apply -f k8s/service.yaml
kubectl apply -f k8s/ingress.yaml
```

Serverless (AWS Lambda)

```bash
# Package for Lambda
cd backend
pip install -r requirements.txt -t ./package
cd package
zip -r ../lambda_deployment.zip .

# Deploy with SAM
sam deploy --guided
```

🤝 Contributing

1. Fork the repository
2. Create a feature branch (git checkout -b feature/amazing-feature)
3. Commit changes (git commit -m 'Add amazing feature')
4. Push to branch (git push origin feature/amazing-feature)
5. Open a Pull Request

Development Guidelines

· Follow PEP 8 for Python code
· Use TypeScript for frontend
· Write tests for new features
· Update documentation
· Use conventional commits

📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

🙏 Acknowledgments

· Built with FastAPI, React, and PostgreSQL
· Uses OpenAI's GPT models for AI capabilities
· Inspired by AutoGPT and LangChain
· Icons by Lucide React
· UI components with Tailwind CSS

🆘 Support

· 📖 Documentation
· 🐛 Issue Tracker
· 💬 Discord Community
· 📧 Email Support

---

<div align="center">
Made with ❤️ by the Agent OS Team (So, from me, 1 employee 🤷🏻‍♂️)

</div>
```
