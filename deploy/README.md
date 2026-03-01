# GCP Deployment for CapperSuite Live

This version of CapperSuite is optimized to run 24/7 on a Google Cloud Platform (GCP) "Always Free" e2-micro compute instance.

## 1. Provision VM
- **Machine Type**: e2-micro (0.25 vCPU, 1 GB memory)
- **Region**: us-central1, us-east1, or us-west1 (for Always Free tier)
- **OS**: Debian 12 or Ubuntu 22.04 LTS
- **Boot Disk**: 30 GB standard persistent disk

## 2. Setup Server
SSH into the machine and install Docker:
```bash
sudo apt update && sudo apt install -y docker.io git nano
sudo systemctl enable --now docker
sudo usermod -aG docker $USER
```

## 3. Clone Repository
*(Note: You may need to generate SSH keys or use HTTPS with a Personal Access Token)*
```bash
git clone <your-repo-url> cappersuite-live
cd cappersuite-live
```

## 4. Configure Environment
```bash
cp .env.example .env
nano .env
```
Fill in at minimum:
- `API_ID`
- `API_HASH`
- `TARGET_TELEGRAM_CHANNEL_ID` (comma separated)
- `OPENROUTER_API_KEY`
- `SUPABASE_URL`
- `SUPABASE_KEY`

## 5. First-Time Authentication (CRITICAL)
Before running in the background, you **MUST** run the script interactively once to input the Telegram 2FA code.
```bash
# Build the local Docker image
docker build -t cappersuite-live -f deploy/Dockerfile .

# Run interactively, sharing the current directory to capture the session file
docker run -it --rm -v $(pwd)/data:/app/data cappersuite-live
```
Follow the prompts, enter your phone number and 2FA code. Once it says "Listening for new messages", press `Ctrl+C` to stop it. The session is now saved in `./data/sessions/`.

## 6. Run 24/7
Now you can start it in detached mode so it runs forever:
```bash
docker run -d --name cappersuite-live --restart unless-stopped -v $(pwd)/data:/app/data cappersuite-live
```

View logs:
```bash
docker logs -f cappersuite-live
```
