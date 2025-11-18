# Moving MongoDB Database to Remote Server

This guide explains how to deploy a local MIMIC-III MongoDB database to a remote MongoDB server or MongoDB Atlas.

## Current State
- **Local Database**: `mimic_iii_nosql` on `localhost:27017`
  - 10,000 patients with embedded admissions, ICU stays, diagnoses, and notes
  - Total data size: ~609 MB
- **Atlas Deployment**: Successfully deployed to MongoDB Atlas
  - 8,518 patients (85% of dataset)
  - Limited by M0 free tier 512 MB storage quota

---

## Option 1: MongoDB Atlas (Recommended for Cloud Hosting)

MongoDB Atlas provides a free M0 cloud database tier suitable for school projects, with automatic backups and monitoring.

**Important:** The M0 free tier has a **512 MB storage limit**. The full MIMIC-III dataset (~609 MB) exceeds this limit. You can deploy approximately **8,500 patients** (85% of the dataset) which is sufficient for project demonstration.

### Step 1: Create MongoDB Atlas Cluster

1. Sign up at https://www.mongodb.com/cloud/atlas
2. Create a new cluster (M0 free tier: 512 MB storage, shared RAM)
3. Choose your cloud provider and region
4. Create a database user:
   - Username: e.g., `your_db_user`
   - Password: Generate a secure password (save it!)
5. Add your IP address to the IP whitelist:
   - Use `0.0.0.0/0` for development (allows all IPs)
   - Or add your specific IP for better security

### Step 2: Export Local Database

```bash
# Export your local MongoDB database
mongodump --db mimic_iii_nosql --out /tmp/mongodb_backup

# Check the backup size
du -sh /tmp/mongodb_backup/mimic_iii_nosql
```

### Step 3: Get Atlas Connection String

From Atlas Dashboard:
1. Click "Connect" on your cluster
2. Choose "Connect your application"
3. Copy the connection string (format: `mongodb+srv://...`)

Example:
```
mongodb+srv://mimic_user:<password>@cluster0.xxxxx.mongodb.net/
```

### Step 4: Restore to Atlas

```bash
# Restore to Atlas (replace with your connection string)
mongorestore \
  --uri="mongodb+srv://your_user:YOUR_PASSWORD@cluster0.xxxxx.mongodb.net/mimic_iii_nosql" \
  /tmp/mongodb_backup/mimic_iii_nosql

# Note: You may see a "space quota" error after ~8,500 patients
# This is expected with the 512 MB free tier limit

# Verify the restore
mongosh "mongodb+srv://your_user:YOUR_PASSWORD@cluster0.xxxxx.mongodb.net/mimic_iii_nosql" \
  --eval "db.patients.countDocuments({})"
```

**Expected output**: `8518` (or similar, depending on when quota is hit)

**Note:** The restore will stop at ~85% completion due to the 512 MB storage limit. This is sufficient for project demonstration.

### Step 5: Update Migration Configuration

Edit `/Users/dayveid/SOEN363Proj/migration/.env`:

```env
# MongoDB Atlas Configuration
MONGODB_HOST=cluster0.xxxxx.mongodb.net
MONGODB_DATABASE=mimic_iii_nosql
MONGODB_USERNAME=mimic_user
MONGODB_PASSWORD=your_atlas_password
MONGODB_AUTH_SOURCE=admin
MONGODB_TLS=true
MONGODB_SRV=true
```

### Step 6: Test Connection

```bash
cd /Users/dayveid/SOEN363Proj/migration
source venv/bin/activate
python -c "
from load_mongodb import MongoDBLoader
loader = MongoDBLoader()
if loader.connect():
    count = loader.get_collection_count('patients')
    print(f'✓ Connected to Atlas! Patient count: {count}')
    loader.disconnect()
else:
    print('✗ Connection failed')
"
```

### Step 7: Run Validation

```bash
python validate_migration.py
```

**Expected**: All 6 tests should pass

---

## Option 2: Self-Hosted Remote MongoDB Server

For deploying MongoDB on your own server (AWS EC2, DigitalOcean, etc.)

### Step 1: Install MongoDB on Remote Server

SSH into your remote server:

```bash
ssh username@your-remote-server.com
```

Install MongoDB (Ubuntu/Debian):

```bash
# Import MongoDB public GPG key
wget -qO - https://www.mongodb.org/static/pgp/server-8.0.asc | sudo apt-key add -

# Add MongoDB repository
echo "deb [ arch=amd64,arm64 ] https://repo.mongodb.org/apt/ubuntu jammy/mongodb-org/8.0 multiverse" | \
  sudo tee /etc/apt/sources.list.d/mongodb-org-8.0.list

# Install MongoDB
sudo apt-get update
sudo apt-get install -y mongodb-org

# Start MongoDB
sudo systemctl start mongod
sudo systemctl enable mongod
```

### Step 2: Configure MongoDB for Remote Access

Edit MongoDB configuration:

```bash
sudo nano /etc/mongod.conf
```

Update the following:

```yaml
# Network interfaces
net:
  port: 27017
  bindIp: 0.0.0.0  # Changed from 127.0.0.1 to allow remote connections

# Security
security:
  authorization: enabled  # Enable authentication
```

Restart MongoDB:

```bash
sudo systemctl restart mongod
```

### Step 3: Create MongoDB Users

Connect to MongoDB:

```bash
mongosh
```

Create admin and database users:

```javascript
// Switch to admin database
use admin

// Create admin user
db.createUser({
  user: "admin",
  pwd: "your_admin_password",
  roles: [ { role: "root", db: "admin" } ]
})

// Switch to your application database
use mimic_iii_nosql

// Create application user
db.createUser({
  user: "mimic_user",
  pwd: "your_secure_password",
  roles: [
    { role: "readWrite", db: "mimic_iii_nosql" },
    { role: "dbAdmin", db: "mimic_iii_nosql" }
  ]
})

exit
```

### Step 4: Configure Firewall

```bash
# Allow MongoDB port
sudo ufw allow 27017/tcp

# Or restrict to specific IP
sudo ufw allow from YOUR_CLIENT_IP to any port 27017
```

### Step 5: Transfer Data to Remote Server

From your local machine:

```bash
# Export local database
mongodump --db mimic_iii_nosql --out /tmp/mongodb_backup

# Compress for faster transfer
tar -czf mongodb_backup.tar.gz -C /tmp mongodb_backup

# Copy to remote server
scp mongodb_backup.tar.gz username@your-remote-server.com:/tmp/

# SSH into remote server
ssh username@your-remote-server.com

# Extract backup
cd /tmp
tar -xzf mongodb_backup.tar.gz

# Restore to MongoDB
mongorestore \
  --username mimic_user \
  --password your_secure_password \
  --authenticationDatabase mimic_iii_nosql \
  --db mimic_iii_nosql \
  /tmp/mongodb_backup/mimic_iii_nosql

# Verify
mongosh --username mimic_user --password your_secure_password \
  --authenticationDatabase mimic_iii_nosql \
  mimic_iii_nosql \
  --eval "db.patients.countDocuments({})"
```

**Expected output**: `10000`

### Step 6: Update Local Configuration

Edit `/migration/.env`:

```env
# Remote MongoDB Configuration
MONGODB_HOST=your-remote-server.com
MONGODB_PORT=27017
MONGODB_DATABASE=mimic_iii_nosql
MONGODB_USERNAME=mimic_user
MONGODB_PASSWORD=your_secure_password
MONGODB_AUTH_SOURCE=admin
MONGODB_TLS=false
MONGODB_SRV=false
```

### Step 7: Test Remote Connection

```bash
cd /Users/dayveid/SOEN363Proj/migration
source venv/bin/activate

# Test connection
python -c "
from load_mongodb import MongoDBLoader
loader = MongoDBLoader()
if loader.connect():
    count = loader.get_collection_count('patients')
    print(f'✓ Connected to remote server! Patient count: {count}')
    loader.disconnect()
else:
    print('✗ Connection failed')
"
```

### Step 8: Run Validation

```bash
python validate_migration.py
```

---

## Option 3: Docker Deployment

Deploy MongoDB in a Docker container on a remote server.

### On Remote Server

```bash
# Pull MongoDB image
docker pull mongo:8.0

# Run MongoDB with authentication
docker run -d \
  --name mongodb \
  -p 27017:27017 \
  -e MONGO_INITDB_ROOT_USERNAME=admin \
  -e MONGO_INITDB_ROOT_PASSWORD=your_admin_password \
  -e MONGO_INITDB_DATABASE=mimic_iii_nosql \
  -v mongodb_data:/data/db \
  mongo:8.0

# Create application user
docker exec -it mongodb mongosh -u admin -p your_admin_password --authenticationDatabase admin

use mimic_iii_nosql
db.createUser({
  user: "mimic_user",
  pwd: "your_secure_password",
  roles: [ { role: "readWrite", db: "mimic_iii_nosql" } ]
})
exit
```

Then follow Steps 5-8 from Option 2 to transfer data and configure your local environment.

---

## Troubleshooting

### Connection Timeout

**Issue**: Cannot connect to remote MongoDB

**Solutions**:
1. Check firewall rules: `sudo ufw status`
2. Verify MongoDB is listening: `sudo netstat -plnt | grep 27017`
3. Test connectivity: `telnet your-remote-server.com 27017`
4. Check MongoDB logs: `sudo tail -f /var/log/mongodb/mongod.log`

### Authentication Failed

**Issue**: `Authentication failed` error

**Solutions**:
1. Verify username/password in `.env`
2. Check auth source: should be `admin` or database name
3. Recreate user if needed:
   ```javascript
   use admin
   db.dropUser("mimic_user")
   // Create user again
   ```

### SSL/TLS Errors (Atlas)

**Issue**: SSL certificate verification failed

**Solution**: Ensure `MONGODB_TLS=true` and `MONGODB_SRV=true` in `.env`

### IP Whitelist (Atlas)

**Issue**: Connection refused by Atlas

**Solution**: Add your IP address to Atlas IP whitelist in Atlas Dashboard → Network Access

### Storage Quota Exceeded (Atlas)

**Issue**: `you are over your space quota, using 524 MB of 512 MB`

**This is expected** with the full MIMIC-III dataset. Solutions:
1. **Keep partial data** (recommended): 8,500 patients is sufficient for project demonstration
2. **Remove old ICD reference collection** if it exists: `db.icd_diagnoses.drop()`
3. **Migrate fewer patients locally**: Modify migration script to process only 8,000 patients
4. **Upgrade to M10**: ~$57/month for 10GB storage (not necessary for school project)

---

## Performance Considerations

### Atlas Free Tier (M0)
- **Storage**: 512 MB limit (hard cap)
- **RAM**: Shared across users
- **Current Usage**: ~520 MB (full - contains 8,518 patients)
- **Connections**: Limited to 500 concurrent
- **Performance**: Suitable for development and school projects

### Note on Paid Tiers
For larger projects exceeding the free tier limits, paid tiers start at ~$57/month (M10), but the M0 free tier may be insufficient for this project.

### Self-Hosted Server Requirements
- **RAM**: 2 GB minimum, 4 GB recommended
- **Storage**: 10 GB minimum (with room for growth)
- **CPU**: 2 cores recommended
- **Network**: Stable connection with low latency

---

## Security Best Practices

1. **Strong Passwords**: Use secure passwords with special characters
2. **IP Whitelisting**: Restrict MongoDB access to known IPs (or use 0.0.0.0/0 for development)
3. **TLS/SSL**: Use encryption for connections (required for Atlas)
4. **User Permissions**: Create database users with appropriate read/write access
5. **Keep Credentials Private**: Never commit `.env` files to version control

---

## Reverting to Local MongoDB

To switch back to local MongoDB:

1. Update `.env`:
   ```env
   MONGODB_HOST=localhost
   MONGODB_PORT=27017
   MONGODB_DATABASE=mimic_iii_nosql
   MONGODB_USERNAME=
   MONGODB_PASSWORD=
   MONGODB_TLS=false
   MONGODB_SRV=false
   ```

2. Restart local MongoDB: `brew services restart mongodb-community`

3. Test: `python validate_migration.py`

---

## Additional Resources

- **MongoDB Atlas Documentation**: https://docs.atlas.mongodb.com/
- **MongoDB Security Checklist**: https://docs.mongodb.com/manual/administration/security-checklist/
- **Connection String Format**: https://docs.mongodb.com/manual/reference/connection-string/
- **MongoDB Backup Strategies**: https://docs.mongodb.com/manual/core/backups/

---

## Need Help?

Check the troubleshooting section or review:
- `migration.log` for detailed error messages
- MongoDB logs: `/var/log/mongodb/mongod.log` (Linux)
- Connection string format in `config.py`
- MongoDB documentation and community forums
