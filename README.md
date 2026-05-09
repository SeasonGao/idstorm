# idstorm

conda activate idstorm

uvicorn app.main:app --reload

npm run dev

claude --dangerously-skip-permissions



docker build -t idstorm:v1.0 .

docker run -d --name idstorm -p 8080:80 idstorm:v1.0

http://localhost:8080

docker logs -f idstorm
