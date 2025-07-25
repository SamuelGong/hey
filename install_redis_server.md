# Install and Run Redis-Server without Root Privileges

## 1. OpenEuler

Prerequisite `Git LFS`:

```bash
git clone https://gitee.com/src-openeuler/redis.git
git lfs install
git lfs pull
tar -zxvf redis-8.0.3.tar.gz  # or any presenting version
cd redis-8.0.3
make
cd src
./redis-server &
```

## 2. Other Linux Systems

Reference: https://techmonger.github.io/40/redis-without-root/

```bash
wget https://download.redis.io/releases/redis-7.0.15.tar.gz
tar -xf redis-7.0.15.tar.gz
cd redis-7.0.15
make
cd src
./redis-server &
```