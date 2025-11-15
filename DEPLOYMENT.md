# NovaAvatar Deployment Guide

This guide covers deploying NovaAvatar to production environments.

## Table of Contents

- [Prerequisites](#prerequisites)
- [Docker Deployment](#docker-deployment)
- [Kubernetes Deployment](#kubernetes-deployment)
- [Cloud Deployments](#cloud-deployments)
  - [AWS](#aws-deployment)
  - [Google Cloud](#google-cloud-deployment)
  - [Azure](#azure-deployment)
- [Configuration](#configuration)
- [Monitoring](#monitoring)
- [Scaling](#scaling)
- [Troubleshooting](#troubleshooting)

## Prerequisites

### Hardware Requirements

**Minimum (1.3B model):**
- CPU: 4+ cores
- RAM: 16GB
- GPU: NVIDIA GPU with 12GB+ VRAM
- Storage: 100GB SSD

**Recommended (14B model):**
- CPU: 8+ cores
- RAM: 32GB
- GPU: NVIDIA GPU with 24GB+ VRAM (e.g., RTX 4090, A5000)
- Storage: 200GB NVMe SSD

### Software Requirements

- Docker 24+ with NVIDIA Container Toolkit
- Docker Compose v2+
- NVIDIA Driver 535+ (for CUDA 12.4)
- PostgreSQL 16+ (or use Docker)
- Redis 7+ (or use Docker)

## Docker Deployment

### Quick Deploy with Docker Compose

1. **Clone the repository:**
   ```bash
   git clone https://github.com/BusinessBuilders/NovaAvatar.git
   cd NovaAvatar
   ```

2. **Configure environment:**
   ```bash
   cp .env.example .env
   nano .env  # Edit with your API keys and settings
   ```

3. **Download models:**
   ```bash
   # For 1.3B model
   huggingface-cli download Wan-AI/Wan2.1-T2V-1.3B --local-dir ./pretrained_models/Wan2.1-T2V-1.3B
   huggingface-cli download OmniAvatar/OmniAvatar-1.3B --local-dir ./pretrained_models/OmniAvatar-1.3B
   huggingface-cli download facebook/wav2vec2-base-960h --local-dir ./pretrained_models/wav2vec2-base-960h
   ```

4. **Start services:**
   ```bash
   docker-compose up -d
   ```

5. **Initialize database:**
   ```bash
   docker-compose exec api alembic upgrade head
   ```

6. **Verify deployment:**
   ```bash
   curl http://localhost:8000/health
   ```

### Production Docker Compose

For production, use the production compose file:

```bash
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```

## Kubernetes Deployment

### Using Helm Chart

```bash
# Add Helm repository
helm repo add novaavatar https://businessbuilders.github.io/novaavatar-helm

# Install with custom values
helm install novaavatar novaavatar/novaavatar \
  --set apiKey=your-api-key \
  --set replicaCount=3 \
  --set resources.limits.nvidia\.com/gpu=1
```

### Manual Kubernetes Deployment

1. **Create namespace:**
   ```bash
   kubectl create namespace novaavatar
   ```

2. **Create secrets:**
   ```bash
   kubectl create secret generic novaavatar-secrets \
     --from-literal=openai-api-key='sk-...' \
     --from-literal=replicate-token='r8_...' \
     --from-literal=database-url='postgresql://...' \
     -n novaavatar
   ```

3. **Deploy PostgreSQL:**
   ```bash
   kubectl apply -f k8s/postgres.yaml -n novaavatar
   ```

4. **Deploy Redis:**
   ```bash
   kubectl apply -f k8s/redis.yaml -n novaavatar
   ```

5. **Deploy NovaAvatar:**
   ```bash
   kubectl apply -f k8s/deployment.yaml -n novaavatar
   kubectl apply -f k8s/service.yaml -n novaavatar
   kubectl apply -f k8s/ingress.yaml -n novaavatar
   ```

6. **Run migrations:**
   ```bash
   kubectl exec -it deployment/novaavatar-api -n novaavatar -- alembic upgrade head
   ```

## Cloud Deployments

### AWS Deployment

#### Using EC2 with GPU

1. **Launch GPU instance:**
   - Instance type: `g5.xlarge` or `g5.2xlarge`
   - AMI: Deep Learning AMI (Ubuntu)
   - Security groups: Open ports 8000, 7860, 22

2. **SSH and install:**
   ```bash
   ssh -i key.pem ubuntu@ec2-instance
   git clone https://github.com/BusinessBuilders/NovaAvatar.git
   cd NovaAvatar
   make setup
   make docker-up
   ```

3. **Set up load balancer:**
   - Create Application Load Balancer
   - Target group: EC2 instance on port 8000
   - Health check: `/health`

#### Using ECS with Fargate

```bash
# Build and push image
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin <account-id>.dkr.ecr.us-east-1.amazonaws.com
docker build -t novaavatar .
docker tag novaavatar:latest <account-id>.dkr.ecr.us-east-1.amazonaws.com/novaavatar:latest
docker push <account-id>.dkr.ecr.us-east-1.amazonaws.com/novaavatar:latest

# Deploy with ECS CLI
ecs-cli compose --file docker-compose.yml service up
```

### Google Cloud Deployment

#### Using Compute Engine with GPU

```bash
# Create instance with GPU
gcloud compute instances create novaavatar \
  --zone=us-central1-a \
  --machine-type=n1-standard-8 \
  --accelerator=type=nvidia-tesla-t4,count=1 \
  --image-family=pytorch-latest-gpu \
  --image-project=deeplearning-platform-release \
  --maintenance-policy=TERMINATE \
  --boot-disk-size=200GB

# SSH and deploy
gcloud compute ssh novaavatar --zone=us-central1-a
git clone https://github.com/BusinessBuilders/NovaAvatar.git
cd NovaAvatar
make setup docker-up
```

#### Using Google Kubernetes Engine (GKE)

```bash
# Create cluster with GPUs
gcloud container clusters create novaavatar-cluster \
  --accelerator type=nvidia-tesla-t4,count=1 \
  --zone us-central1-a \
  --num-nodes=2

# Deploy
kubectl apply -f k8s/
```

### Azure Deployment

#### Using Azure Container Instances

```bash
# Create resource group
az group create --name novaavatar-rg --location eastus

# Create container
az container create \
  --resource-group novaavatar-rg \
  --name novaavatar \
  --image businessbuilders/novaavatar:latest \
  --gpu-count 1 \
  --gpu-sku T4 \
  --cpu 4 \
  --memory 16 \
  --ports 8000 7860 \
  --environment-variables \
    OPENAI_API_KEY=$OPENAI_API_KEY \
    DATABASE_URL=$DATABASE_URL
```

## Configuration

### Production Environment Variables

```bash
# API Keys
OPENAI_API_KEY=sk-...
REPLICATE_API_TOKEN=r8_...

# Database
DATABASE_URL=postgresql://user:pass@host:5432/novaavatar
REDIS_URL=redis://host:6379

# Model Configuration
USE_14B_MODEL=true
ENABLE_VRAM_MANAGEMENT=true
NUM_STEPS=25
TEA_CACHE_THRESH=0.14

# Server
API_SERVER_HOST=0.0.0.0
API_SERVER_PORT=8000
GRADIO_SERVER_PORT=7860

# Monitoring
SENTRY_DSN=https://...@sentry.io/...
PROMETHEUS_ENABLED=true

# Security
AUTO_APPROVE=false
RATE_LIMIT_PER_MINUTE=100
```

### Nginx Reverse Proxy

```nginx
upstream novaavatar_api {
    server localhost:8000;
}

upstream novaavatar_frontend {
    server localhost:7860;
}

server {
    listen 80;
    server_name api.novaavatar.com;

    location / {
        proxy_pass http://novaavatar_api;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # WebSocket support
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";

        # Timeouts
        proxy_connect_timeout 60s;
        proxy_send_timeout 600s;
        proxy_read_timeout 600s;
    }
}

server {
    listen 80;
    server_name novaavatar.com;

    location / {
        proxy_pass http://novaavatar_frontend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

## Monitoring

### Prometheus + Grafana

1. **Access Grafana:** http://your-server:3000
2. **Default credentials:** admin/admin
3. **Add Prometheus data source:** http://prometheus:9090
4. **Import dashboards:** Use dashboard IDs from `monitoring/grafana/dashboards/`

### Sentry Error Tracking

Configure in `.env`:
```bash
SENTRY_DSN=https://...@sentry.io/...
SENTRY_ENVIRONMENT=production
```

### Health Checks

```bash
# Kubernetes liveness probe
livenessProbe:
  httpGet:
    path: /health/live
    port: 8000
  initialDelaySeconds: 30
  periodSeconds: 10

# Kubernetes readiness probe
readinessProbe:
  httpGet:
    path: /health/ready
    port: 8000
  initialDelaySeconds: 10
  periodSeconds: 5
```

## Scaling

### Horizontal Scaling

```bash
# Kubernetes
kubectl scale deployment novaavatar-api --replicas=3

# Docker Compose
docker-compose up -d --scale api=3
```

### Load Balancing

Use a load balancer to distribute traffic:
- **AWS**: Application Load Balancer
- **GCP**: Cloud Load Balancing
- **Azure**: Azure Load Balancer
- **Self-hosted**: Nginx, HAProxy

### Auto-scaling

**Kubernetes HPA:**
```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: novaavatar-api-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: novaavatar-api
  minReplicas: 2
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
```

## Troubleshooting

### Common Issues

**GPU Not Detected:**
```bash
# Check NVIDIA driver
nvidia-smi

# Check Docker GPU access
docker run --gpus all nvidia/cuda:12.4.0-base-ubuntu22.04 nvidia-smi

# Install NVIDIA Container Toolkit
distribution=$(. /etc/os-release;echo $ID$VERSION_ID)
curl -s -L https://nvidia.github.io/nvidia-docker/gpgkey | sudo apt-key add -
curl -s -L https://nvidia.github.io/nvidia-docker/$distribution/nvidia-docker.list | sudo tee /etc/apt/sources.list.d/nvidia-docker.list
sudo apt-get update && sudo apt-get install -y nvidia-container-toolkit
sudo systemctl restart docker
```

**Out of Memory:**
```bash
# Use 1.3B model instead of 14B
USE_14B_MODEL=false

# Enable VRAM management
ENABLE_VRAM_MANAGEMENT=true

# Reduce batch size/steps
NUM_STEPS=20
```

**Database Connection Issues:**
```bash
# Check connectivity
psql $DATABASE_URL

# Run migrations
alembic upgrade head

# Reset database (DANGER!)
alembic downgrade base
alembic upgrade head
```

**High Latency:**
- Enable TeaCache: `TEA_CACHE_THRESH=0.14`
- Use SSD storage
- Increase worker processes
- Add caching layer (Redis)

## Security Best Practices

1. **Use HTTPS:** Configure SSL/TLS certificates
2. **API Keys:** Rotate regularly, use environment variables
3. **Database:** Use strong passwords, restrict network access
4. **Firewall:** Only expose necessary ports
5. **Updates:** Keep dependencies and system updated
6. **Backups:** Regular database and model backups
7. **Monitoring:** Set up alerts for anomalies

## Backup and Recovery

### Database Backup

```bash
# Backup
pg_dump $DATABASE_URL > backup_$(date +%Y%m%d).sql

# Restore
psql $DATABASE_URL < backup_20240101.sql
```

### Automated Backups

```bash
# Cron job for daily backups
0 2 * * * pg_dump $DATABASE_URL | gzip > /backups/novaavatar_$(date +\%Y\%m\%d).sql.gz
```

## Support

- **Documentation:** https://github.com/BusinessBuilders/NovaAvatar
- **Issues:** https://github.com/BusinessBuilders/NovaAvatar/issues
- **Discussions:** https://github.com/BusinessBuilders/NovaAvatar/discussions
