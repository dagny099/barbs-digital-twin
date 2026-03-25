# Uptime Kuma deployment guide (Amazon Linux)

A step-by-step guide for deploying Uptime Kuma on your EC2 instance, configuring monitors for your full portfolio stack, and publishing a public status page at `status.barbhs.com`.

---

## Phase 0: Understand what we're building

**Uptime Kuma** is a self-hosted monitoring tool that runs as a single Docker container. It periodically sends health check requests to your services and records whether they respond correctly. It also serves a beautiful, public-facing status page — the thing your portfolio visitors will see.

**Why Docker?** Docker packages Kuma and all its dependencies into an isolated container. This means it won't conflict with anything else on your EC2 instance, and if something goes wrong, you can destroy and recreate it in seconds without affecting your other apps. Think of it as a lightweight virtual machine that starts in under a second.

**What Kuma will check:**

| Service | Check type | What it verifies |
|---------|-----------|-----------------|
| barbhs.com | HTTP(s) | Returns 200, loads in < 5s |
| Resume Explorer (Vercel frontend) | HTTP(s) | Returns 200 |
| Resume Explorer (Railway backend) | HTTP(s) + keyword | Returns 200 AND response contains expected string |
| Digital Twin (HuggingFace) | HTTP(s) | Returns 200 (Gradio health endpoint) |
| Concept Cartographer (EC2) | HTTP(s) | Returns 200 on localhost |
| RDS Postgres | TCP port | Can connect to port 5432 |
| Neo4j | HTTP(s) | Neo4j browser/API responds on its HTTP port |

---

## Phase 1: Prepare your EC2 instance

### Step 1.1 — SSH into your instance

```bash
ssh -i your-key.pem ec2-user@your-ec2-ip
```

Replace `your-key.pem` and `your-ec2-ip` with your actual values. The default user for Amazon Linux is `ec2-user`.

### Step 1.2 — Check your available RAM

```bash
free -h
```

You'll see output like:

```
              total        used        free      shared  buff/cache   available
Mem:           983M        612M         72M         4M        298M        220M
```

Look at the `available` column. If it's under 300MB, the swap file in the next step is essential, not optional.

**Why:** Your earlier EC2 audit found RAM pressure on the t2.micro. Kuma needs ~150-200MB to run comfortably.

### Step 1.3 — Create a swap file (insurance policy)

A swap file lets Linux use disk space as overflow memory. It's slower than RAM but prevents out-of-memory crashes. On a t2.micro with 1GB RAM, this is essential.

```bash
# Create a 1GB swap file
sudo fallocate -l 1G /swapfile

# Set correct permissions (only root should read/write swap)
sudo chmod 600 /swapfile

# Format it as swap space
sudo mkswap /swapfile

# Turn it on immediately
sudo swapon /swapfile

# Verify it's active — you should now see a "Swap" row with 1.0G total
free -h
```

Now make it permanent so it survives reboots:

```bash
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
```

**Why:** Without swap, if your apps + Kuma exceed 1GB RAM, the Linux OOM killer will randomly terminate processes. This 30-second step prevents that.

### Step 1.4 — Install Docker (if not already installed)

First check if Docker is already there:

```bash
docker --version
```

If you get a version number, skip to Phase 2. If "command not found," install it:

```bash
# Update packages
sudo yum update -y

# Install Docker
sudo yum install docker -y

# Start Docker and enable it on boot
sudo systemctl start docker
sudo systemctl enable docker

# Add your user to the docker group (so you don't need sudo every time)
sudo usermod -aG docker ec2-user

# Apply the group change without logging out
newgrp docker

# Verify it works — you should see "Hello from Docker!"
docker run hello-world
```

**Why each command matters:**
- `systemctl enable` = Docker starts automatically when EC2 reboots
- `usermod -aG docker` = lets you run `docker` commands without `sudo` every time
- `newgrp docker` = activates the group change in your current session

**If `newgrp` doesn't seem to work:** Log out and SSH back in. The group change always takes effect on next login.

---

## Phase 2: Deploy Uptime Kuma

### Step 2.1 — Create a persistent data directory

```bash
mkdir -p ~/kuma-data
```

**Why:** Kuma stores its configuration, monitor history, and status page settings in a SQLite database. By mapping this directory into the container, your data survives even if you destroy and recreate the container. Think of it as the container's "save file."

### Step 2.2 — Run the Uptime Kuma container

```bash
docker run -d \
  --name uptime-kuma \
  --restart=unless-stopped \
  -p 3001:3001 \
  -v ~/kuma-data:/app/data \
  louislam/uptime-kuma:1
```

What every flag does:

| Flag | What it does |
|------|-------------|
| `-d` | Runs in the background (detached mode) |
| `--name uptime-kuma` | Gives the container a human-readable name |
| `--restart=unless-stopped` | Auto-restarts on crash or EC2 reboot (unless you manually stop it) |
| `-p 3001:3001` | Maps port 3001 on your EC2 to port 3001 inside the container |
| `-v ~/kuma-data:/app/data` | Mounts your local directory into the container for persistent storage |
| `louislam/uptime-kuma:1` | The Docker image. `:1` pins to the latest 1.x release (stable) |

### Step 2.3 — Verify it's running

```bash
# Should show uptime-kuma with status "Up X seconds"
docker ps

# Test the web UI is responding locally
curl -s http://localhost:3001 | head -5
```

If you see HTML output, Kuma is alive. If not, check logs:

```bash
docker logs uptime-kuma
```

### Step 2.4 — Open port 3001 temporarily in your security group

In the AWS Console:

1. Go to **EC2 → Instances → click your instance → Security tab → click the security group link**
2. Click **Edit inbound rules**
3. **Add rule:** Custom TCP, Port 3001, Source = **My IP**
4. Save rules

**Critical: choose "My IP," not "Anywhere."** This is the raw admin interface — you're exposing it temporarily just to run the setup wizard. We'll lock it down later behind Nginx + HTTPS.

### Step 2.5 — Create your admin account

Open your browser and navigate to:

```
http://YOUR_EC2_PUBLIC_IP:3001
```

You'll see the Uptime Kuma setup wizard. Create your admin username and a strong password. This dashboard gives full control over your monitors, so treat the credentials seriously.

---

## Phase 3: Configure your monitors

Once logged in, click **"Add New Monitor"** for each service. Here's exactly what to enter for each one.

### 3.1 — barbhs.com (GitHub Pages)

| Setting | Value |
|---------|-------|
| Monitor Type | HTTP(s) |
| Friendly Name | `barbhs.com` |
| URL | `https://barbhs.com` |
| Heartbeat Interval | `300` (seconds — every 5 min) |
| Retries | `3` |
| Expected Status Code | `200` |

**Why 5-minute intervals?** GitHub Pages is extremely stable. More frequent checks waste resources and can look like suspicious traffic.

### 3.2 — Resume Explorer frontend (Vercel)

| Setting | Value |
|---------|-------|
| Monitor Type | HTTP(s) |
| Friendly Name | `Resume Explorer (frontend)` |
| URL | Your Vercel deployment URL |
| Heartbeat Interval | `300` |
| Retries | `3` |
| Expected Status Code | `200` |

### 3.3 — Resume Explorer backend (Railway)

| Setting | Value |
|---------|-------|
| Monitor Type | HTTP(s) - Keyword |
| Friendly Name | `Resume Explorer (API)` |
| URL | Your Railway URL + `/health` endpoint |
| Heartbeat Interval | `300` |
| Keyword | `ok` (or whatever your health endpoint returns) |
| Keyword should | `Exist` |

**Why keyword check instead of just HTTP 200?** A web server can return 200 even when the app behind it is broken (e.g., Railway's reverse proxy serves a default page). Checking for a specific keyword proves your actual Flask app is running and responding.

**If you don't have a `/health` endpoint yet,** add one before configuring this monitor. In Flask it's three lines:

```python
@app.route('/health')
def health():
    return jsonify({"status": "ok"})
```

This is a best practice for any deployed API — it gives load balancers, monitors, and orchestrators a reliable signal.

### 3.4 — Digital Twin (HuggingFace Spaces)

| Setting | Value |
|---------|-------|
| Monitor Type | HTTP(s) |
| Friendly Name | `Digital Twin` |
| URL | `https://YOUR-HF-SPACE.hf.space/` |
| Heartbeat Interval | `600` (every 10 min) |
| Retries | `5` |
| Retry Interval | `30` (seconds between retries) |

**Why the generous retry settings?** HuggingFace free-tier Spaces go to sleep after inactivity. The first request can take 30-60 seconds while the container cold-starts. Without extra retries, you'd get false "down" alerts every time it sleeps.

### 3.5 — Concept Cartographer (EC2 localhost)

| Setting | Value |
|---------|-------|
| Monitor Type | HTTP(s) |
| Friendly Name | `Concept Cartographer` |
| URL | `http://localhost:YOUR_PORT` |
| Heartbeat Interval | `120` (every 2 min) |
| Retries | `3` |

**Why localhost?** Since Kuma runs on the same EC2 instance, it can check internal services directly without going through the public internet. This is faster and doesn't depend on DNS or security group rules.

### 3.6 — RDS Postgres

| Setting | Value |
|---------|-------|
| Monitor Type | TCP Port |
| Friendly Name | `RDS Postgres` |
| Hostname | Your RDS endpoint (e.g., `mydb.abc123.us-east-1.rds.amazonaws.com`) |
| Port | `5432` |
| Heartbeat Interval | `300` |

**Why TCP instead of a SQL query?** Kuma supports a native PostgreSQL monitor type that can run `SELECT 1`, but TCP is simpler to start with and confirms the database is accepting connections. You can upgrade to the PostgreSQL type later if you want deeper checks (it would also verify authentication works).

**Important:** Your RDS security group must allow inbound on port 5432 from your EC2 instance's security group or private IP. If the monitor shows "down" immediately, this is almost certainly the issue.

### 3.7 — Neo4j

| Setting | Value |
|---------|-------|
| Monitor Type | HTTP(s) |
| Friendly Name | `Neo4j` |
| URL | `http://YOUR_NEO4J_HOST:7474` |
| Heartbeat Interval | `300` |
| Expected Status Code | `200` |

**Why HTTP?** Neo4j exposes a browser interface on port 7474 that returns 200 when the database is up. Simplest possible health check.

---

## Phase 4: Set up the public status page

### Step 4.1 — Create the status page in Kuma

1. In the sidebar, click **"Status Pages"**
2. Click **"New Status Page"**
3. Fill in:
   - **Name:** `Portfolio infrastructure`
   - **Slug:** `status` (this becomes the URL path)
4. Click **Save**

### Step 4.2 — Organize monitors into groups

In the status page editor, create groups and drag monitors into them:

**Web applications**
- barbhs.com
- Resume Explorer (frontend)
- Digital Twin
- Concept Cartographer

**API services**
- Resume Explorer (API)

**Databases**
- RDS Postgres
- Neo4j

**Why groups?** Visitors see a clean, tiered view instead of a flat list. It signals you think about infrastructure in layers — presentation, API, data. This is exactly the kind of architectural thinking that impresses in interviews.

---

## Phase 5: Nginx reverse proxy + HTTPS

Right now Kuma is accessible on raw port 3001 with no encryption. We want it at `https://status.barbhs.com`.

### Step 5.1 — Install Nginx

```bash
# On Amazon Linux 2
sudo amazon-linux-extras install nginx1 -y

# On Amazon Linux 2023
sudo yum install nginx -y

# Start and enable
sudo systemctl start nginx
sudo systemctl enable nginx
```

**How to tell which Amazon Linux you're on:**

```bash
cat /etc/os-release | grep PRETTY_NAME
```

If it says "Amazon Linux 2," use the `amazon-linux-extras` command. If "Amazon Linux 2023," use `yum` directly.

### Step 5.2 — Create the Nginx config

```bash
sudo nano /etc/nginx/conf.d/status.barbhs.com.conf
```

Paste this entire block:

```nginx
server {
    listen 80;
    server_name status.barbhs.com;

    location / {
        proxy_pass http://localhost:3001;
        proxy_http_version 1.1;

        # WebSocket support — Kuma uses WebSockets for real-time updates
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";

        # Forward real client info to Kuma
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

Save and exit (`Ctrl+O`, `Enter`, `Ctrl+X` in nano).

**Why each directive matters:**
- `proxy_pass` routes traffic from Nginx to Kuma on port 3001
- The `Upgrade` and `Connection` headers are **critical** — without them, the real-time status updates on the dashboard won't work (the page loads but never auto-refreshes)
- `X-Forwarded-*` headers let Kuma see the real visitor IP and whether they're on HTTPS

### Step 5.3 — Test and reload

```bash
# Check for syntax errors
sudo nginx -t

# If "syntax is ok" and "test is successful":
sudo systemctl reload nginx
```

### Step 5.4 — Point DNS to your EC2

Go to your domain registrar (wherever you manage barbhs.com DNS) and add an A record:

| Type | Name | Value | TTL |
|------|------|-------|-----|
| A | `status` | Your EC2 Elastic IP | 300 |

**Do you have an Elastic IP?** If not, your instance's public IP changes every time it stops and starts, which would break DNS. To allocate one:

1. AWS Console → EC2 → Elastic IPs → **Allocate Elastic IP address**
2. Select the new IP → Actions → **Associate Elastic IP address** → pick your instance
3. Free while the instance is running; $0.005/hr if unattached

After adding the DNS record, wait 2-5 minutes for propagation, then test:

```bash
curl http://status.barbhs.com
```

You should see Kuma's HTML.

### Step 5.5 — Add HTTPS with Let's Encrypt

```bash
# Install certbot and the Nginx plugin
sudo yum install certbot python3-certbot-nginx -y

# Get certificate and auto-configure Nginx for HTTPS
sudo certbot --nginx -d status.barbhs.com
```

Certbot will ask for your email (for renewal notices) and whether to redirect HTTP to HTTPS (say **yes**). It then:
1. Verifies you own the domain
2. Gets a free SSL certificate
3. Rewrites your Nginx config to handle HTTPS
4. Sets up auto-renewal via a systemd timer

Verify auto-renewal is configured:

```bash
sudo certbot renew --dry-run
```

If this succeeds, your certificate will automatically renew before it expires (every ~60 days).

### Step 5.6 — Lock down the security group

Now that Nginx handles all traffic on 80/443, remove the temporary port 3001 rule:

1. AWS Console → EC2 → Security Groups → your instance's group
2. Edit inbound rules → **delete** the port 3001 rule
3. Save

Your final inbound rules should be:

| Port | Protocol | Source | Purpose |
|------|----------|--------|---------|
| 22 | TCP | Your IP | SSH access |
| 80 | TCP | 0.0.0.0/0 | HTTP (redirects to HTTPS) |
| 443 | TCP | 0.0.0.0/0 | HTTPS (status page + Kuma dashboard) |
| (others) | TCP | as needed | Your other apps |

**Note on dashboard access:** After this, the Kuma admin dashboard is also accessible at `https://status.barbhs.com/dashboard`. It's protected by the username/password you created in Step 2.5. The public status page (what visitors see) is at the root URL and requires no login.

---

## Phase 6: Set up notifications

Monitoring is useless if nobody sees the alerts.

### Option A — Email via Gmail (quickest)

If you have a Gmail account, you can use it as an SMTP relay:

1. In your Google account, go to Security → **App passwords** (requires 2FA to be enabled)
2. Generate a new app password for "Mail"
3. In Kuma dashboard → Settings → Notifications → Setup Notification:

| Setting | Value |
|---------|-------|
| Type | SMTP |
| SMTP Host | `smtp.gmail.com` |
| SMTP Port | `587` |
| Security | STARTTLS |
| Username | Your Gmail address |
| Password | The app password (not your regular password) |
| From | Your Gmail address |
| To | Your Gmail address (or wherever you want alerts) |

Click **Test** to confirm it works.

### Option B — Discord webhook (even easier, no email config)

If you have a personal Discord server:

1. Create a channel called `#infra-alerts`
2. Channel Settings → Integrations → Webhooks → New Webhook → Copy URL
3. In Kuma: Notification Type = Discord, paste the webhook URL

---

## Phase 7: Link from your portfolio

### Option A — Subtle footer link

Add to your barbhs.com Jekyll site (e.g., in `_includes/footer.html`):

```html
<a href="https://status.barbhs.com" target="_blank" rel="noopener">
  System Status
</a>
```

### Option B — Badge in GitHub READMEs

Kuma generates embeddable badge URLs. In any monitor's settings, look for the "Badge" section. Copy the Markdown and paste into your project READMEs:

```markdown
![Status](https://status.barbhs.com/api/badge/1/status)
```

### Option C — Dedicated infrastructure page (the portfolio flex)

Create a page on barbhs.com that explains your monitoring setup: the architecture diagram, the tech stack (Docker, Uptime Kuma, Nginx, Let's Encrypt, EC2), and what you learned. This turns a simple ops tool into a case study that demonstrates DevOps fluency. When you're ready for this, I can help you write it up.

---

## Maintenance cheat sheet

```bash
# Is Kuma running?
docker ps | grep kuma

# View recent logs
docker logs uptime-kuma --tail 20

# Restart Kuma
docker restart uptime-kuma

# Check memory usage
free -h

# Check Kuma's database size (grows over time)
du -sh ~/kuma-data

# Update Kuma to latest version
docker pull louislam/uptime-kuma:1
docker stop uptime-kuma
docker rm uptime-kuma
docker run -d \
  --name uptime-kuma \
  --restart=unless-stopped \
  -p 3001:3001 \
  -v ~/kuma-data:/app/data \
  louislam/uptime-kuma:1

# Renew SSL (auto-runs, but just in case)
sudo certbot renew

# Check Nginx status
sudo systemctl status nginx
```

---

## Who watches the watchman?

If your EC2 instance goes down, Kuma goes down with it — and can't alert you. The pragmatic solution: create a free UptimeRobot account (uptimerobot.com) with a single HTTP monitor pointed at `https://status.barbhs.com`. That way you get an email even if your whole instance is unreachable. This takes 2 minutes and costs nothing.

---

## Troubleshooting quick reference

| Symptom | Likely cause | Fix |
|---------|-------------|-----|
| Can't reach port 3001 from browser | Security group doesn't allow it | Add inbound rule for port 3001 from your IP |
| `curl localhost:3001` returns nothing | Kuma container not running | `docker logs uptime-kuma` then re-run the `docker run` command |
| RDS monitor shows "down" immediately | RDS security group blocks EC2 | Add inbound rule on RDS SG for port 5432 from EC2's SG |
| HuggingFace monitor flaps up/down | Space is sleeping between checks | Increase retries to 5, retry interval to 30s |
| Status page loads but doesn't auto-refresh | Missing WebSocket headers in Nginx | Check that `Upgrade` and `Connection` headers are in your Nginx config |
| `certbot` fails domain verification | DNS not propagated yet, or port 80 blocked | Wait 5 min for DNS; ensure port 80 is open in security group |
| Out of memory after deploying Kuma | Swap file not configured | Run Phase 1, Step 1.3 |
