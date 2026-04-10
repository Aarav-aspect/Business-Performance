# Business-Performance
cd /Users/Aarav/Desktop/Archive/SectorPerformance

# Authenticate with GCP
gcloud auth login
gcloud config set project business-performance-492812

# Enable required APIs
gcloud services enable run.googleapis.com containerregistry.googleapis.com cloudbuild.googleapis.com

# Build and push using Cloud Build (no local Docker needed)
gcloud builds submit --tag gcr.io/business-performance-492812/sector-performance
Step 2: Deploy to Cloud Run

gcloud run deploy sector-performance \
  --image gcr.io/business-performance-492812/sector-performance \
  --platform managed \
  --region europe-west2 \
  --allow-unauthenticated \
  --port 8080 \
  --set-env-vars "APP_BASE_PATH=/business-performance,SF_USERNAME=tech@aspect.co.uk,SF_PASSWORD=TuanIsTheBest12,SF_SECURITY_TOKEN=9AHwz5yyDyEP4NulU84JFJdl"
Replace the Salesforce credentials with your actual values. Use europe-west2 (London) for lowest latency to UK users, or change as needed.

Step 3: Route www.aspect.co.uk/business-performance to Cloud Run
This depends on how www.aspect.co.uk is currently hosted:

Option A — If aspect.co.uk already uses a GCP Load Balancer:

Add a Serverless NEG pointing to your Cloud Run service
Add a path rule: /business-performance/* → that NEG
The rest of your site continues to route as before

# Create serverless NEG
gcloud compute network-endpoint-groups create sector-perf-neg \
  --region=europe-west2 \
  --network-endpoint-type=serverless \
  --cloud-run-service=sector-performance

# Add it as a backend service
gcloud compute backend-services create sector-perf-backend \
  --global \
  --load-balancing-scheme=EXTERNAL

gcloud compute backend-services add-backend sector-perf-backend \
  --global \
  --network-endpoint-group=sector-perf-neg \
  --network-endpoint-group-region=europe-west2

# Then in your existing URL map, add a path rule:
gcloud compute url-maps add-path-matcher <your-url-map-name> \
  --path-matcher-name=business-perf-matcher \
  --default-service=<your-existing-backend> \
  --path-rules="/business-performance/*=sector-perf-backend"
Option B — If aspect.co.uk is hosted elsewhere (e.g. Nginx, Apache, Cloudflare):
Add a reverse proxy rule on your existing web server. For example in Nginx:


location /business-performance/ {
    proxy_pass https://<your-cloud-run-url>/business-performance/;
    proxy_set_header Host <your-cloud-run-url>;
    proxy_ssl_server_name on;
}
Get your Cloud Run URL after deploy with:


gcloud run services describe sector-performance --region europe-west2 --format='value(status.url)'
Step 4: Verify
Once routing is set up:


curl https://www.aspect.co.uk/business-performance/api/dashboard
