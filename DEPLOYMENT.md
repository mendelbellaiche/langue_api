# Déploiement sur Ubuntu (Proxmox) — Service systemd natif

## 1. Préparer le serveur

```bash
sudo apt update && sudo apt install -y python3-venv python3-pip git
```

## 2. Récupérer le code et créer le venv

```bash
sudo mkdir -p /opt/langue_api
sudo chown $USER:$USER /opt/langue_api
git clone <ton-repo-url> /opt/langue_api
cd /opt/langue_api
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt gunicorn
```

## 3. Fichier `.env`

Copier le `.env.example` en `.env` (DB, secrets JWT, SMTP, etc.) dans `/opt/langue_api/`, et renseigner les valeurs correspondants.

Important : `DATABASE_URL` doit utiliser le driver `pymysql`, sinon SQLAlchemy tente `MySQLdb` (non installé) :

```
DATABASE_URL=mysql+pymysql://langue_api:MOT_DE_PASSE@localhost:3306/langue_api
```

## 4. Créer un utilisateur système dédié

```bash
sudo useradd --system --no-create-home --shell /usr/sbin/nologin langueapi
sudo chown -R langueapi:langueapi /opt/langue_api
```

## 5. Installer MySQL et créer la base + les tables

```bash
sudo apt install -y mysql-server
sudo systemctl enable --now mysql
sudo mysql_secure_installation
```

Créer un utilisateur applicatif dédié :

```bash
sudo mysql
```

```sql
CREATE USER 'langue_api'@'localhost' IDENTIFIED BY 'MOT_DE_PASSE';
GRANT ALL PRIVILEGES ON langue_api.* TO 'langue_api'@'localhost';
FLUSH PRIVILEGES;
EXIT;
```

Créer la base et les tables via le script du repo :

```bash
mysql -u langue_api -p < /opt/langue_api/sql/schema.sql
```

Vérifier :

```bash
mysql -u langue_api -p -e "USE langue_api; SHOW TABLES;"
```

## 6. Créer le service systemd

`sudo nano /etc/systemd/system/langue-api.service` :

```ini
[Unit]
Description=Langue API (FastAPI/Uvicorn)
After=network.target

[Service]
Type=simple
User=langueapi
Group=langueapi
WorkingDirectory=/opt/langue_api
EnvironmentFile=/opt/langue_api/.env
ExecStart=/opt/langue_api/venv/bin/gunicorn main:app \
    -k uvicorn.workers.UvicornWorker \
    --workers 4 \
    --bind 127.0.0.1:8000 \
    --access-logfile - \
    --error-logfile -
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
```

## 7. Activer et démarrer

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now langue-api
sudo systemctl status langue-api
journalctl -u langue-api -f   # logs en direct
```

## 8. Reverse proxy Nginx ou Apache2

> **HTTPS (Certbot) ne fonctionne que si le domaine est public**, c'est-à-dire que son enregistrement DNS pointe vers une IP publique joignable depuis Internet, et que le port 80/443 est ouvert sur ta box (port forwarding). Pour un accès **local uniquement** (réseau maison, IP privée type `10.0.0.9`, résolu via `/etc/hosts` ou un DNS local), Certbot échouera toujours (`NXDOMAIN`) — reste en HTTP simple (étape 8a), ou utilise un certificat auto-signé/CA interne (mkcert) si tu tiens au HTTPS en local.

### 8a. Nginx

```bash
sudo apt install -y nginx
```

`/etc/nginx/sites-available/langue-api` :

```nginx
server {
    listen 80;
    server_name ton-domaine.fr;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

```bash
sudo ln -s /etc/nginx/sites-available/langue-api /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl reload nginx
```

Accès Swagger : `http://ton-domaine.fr/docs`

**Si le domaine est public**, active le HTTPS avec Certbot :
```bash
sudo apt install -y certbot python3-certbot-nginx
sudo certbot --nginx -d ton-domaine.fr
```
Accès Swagger : `https://ton-domaine.fr/docs`

### 8b. Alternative : Apache2 au lieu de Nginx

```bash
sudo apt install -y apache2
sudo a2enmod proxy proxy_http headers
```

`/etc/apache2/sites-available/langue-api.conf` :

```apache
<VirtualHost *:80>
    ServerName ton-domaine.fr

    ProxyPreserveHost On
    ProxyPass / http://127.0.0.1:8000/
    ProxyPassReverse / http://127.0.0.1:8000/

    RequestHeader set X-Forwarded-Proto "http"
</VirtualHost>
```

```bash
sudo a2ensite langue-api.conf
sudo a2dissite 000-default.conf
sudo apache2ctl configtest && sudo systemctl reload apache2
```

Accès Swagger : `http://ton-domaine.fr/docs`

**Si le domaine est public**, active le HTTPS avec Certbot :
```bash
sudo apt install -y certbot python3-certbot-apache
sudo certbot --apache -d ton-domaine.fr
```
Accès Swagger : `https://ton-domaine.fr/docs`

## 9. Accès sans nom de domaine (test/dev)

Si tu veux accéder directement via l'IP de la VM sans Nginx, changer le bind du service :

```
--bind 0.0.0.0:8000
```

```bash
sudo systemctl daemon-reload
sudo systemctl restart langue-api
```

⚠️ Expose l'API sans HTTPS, à réserver à un usage interne/dev.

Vérifier ensuite le firewall :

```bash
sudo ufw status
sudo ufw allow 8000/tcp   # ou 80/tcp si Nginx
```

Et s'assurer que la VM Proxmox est en réseau **bridge** (pas NAT isolé) pour être joignable depuis l'extérieur.

Accès Swagger : `http://IP-DE-LA-VM:8000/docs`

## 10. Mise à jour du service

```bash
cd /opt/langue_api
sudo -u langueapi git pull
sudo -u langueapi venv/bin/pip install -r requirements.txt
sudo systemctl restart langue-api
```

## 11. Dépannage

**`ModuleNotFoundError: No module named 'MySQLdb'`**
→ `DATABASE_URL` doit contenir `mysql+pymysql://` (pas juste `mysql://`), et `pymysql` doit être installé dans le venv (déjà présent dans `requirements.txt`, sinon) :
```bash
sudo -u langueapi /opt/langue_api/venv/bin/pip install -r requirements.txt
sudo systemctl restart langue-api
```

**Swagger inaccessible depuis le navigateur**
→ Vérifier sur quelle adresse écoute gunicorn :
```bash
sudo ss -tlnp | grep 8000
```
Si `127.0.0.1:8000`, soit passer par Nginx (étape 8), soit changer le bind en `0.0.0.0:8000` (étape 9), puis vérifier le firewall (`ufw`) et le mode réseau de la VM Proxmox (bridge).
