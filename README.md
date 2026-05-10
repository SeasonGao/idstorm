# idstorm

conda activate idstorm

uvicorn app.main:app --reload

npm run dev

claude --dangerously-skip-permissions



docker build -t idstorm:v1.0 .

docker run -d --name idstorm -p 8088:80 idstorm:v1.0

http://localhost:8080

docker logs -f idstorm


docker save -o idstorm.tar idstorm:v1.0

上传到阿里云后，解压

docker load -i idstorm.tar

docker run -d --name idstorm -p xxxx:80 idstorm:v1.0

xxxx需要防火墙开放
