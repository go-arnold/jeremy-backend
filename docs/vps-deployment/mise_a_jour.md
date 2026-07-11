
Le workflow de mise à jour, en résumé :

cd /opt/art-du-kivu-backend

# 1. Récupérer le nouveau code
git pull origin main          # si tu as cloné via git
# — ou, si tu transfères manuellement (rsync/scp) —
# rsync -avz --exclude venv --exclude __pycache__ ./backend/ root@45.151.122.103:/opt/art-du-kivu-backend/

# 2. Reconstruire et relancer api/worker/beat avec le nouveau code
cd docs/vps-deployment
docker compose up -d --build api worker beat

# 3. Vérifier que tout est reparti sainement
docker compose ps
curl -s https://art-du-kivu-api.kelor.tech/api/v1/health/
