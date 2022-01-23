# Setting up a development environment on WSL

We have set up a full fledged e-scriptorium development environment on WSL 2 running Ubuntu 20.04

## Setting up Ubuntu
You need to install Python3.9

```sh
sudo apt update
sudo add-apt-repository ppa:deadsnakes/ppa
sudo apt install python3.9 python3.9-dev python3.9-venv python3-pip
```

And the following package to allow compiling some of the Python packages

```sh
sudo apt install libxml2-dev
```

You also need to install Node, better do it with nvm:

```sh
curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.0/install.sh | bash
nvm install --lts
```

## Preparing the frontend
```sh
cd front
yarn install
```

## Preparing the backend
Create a virtual environment first

```sh
cd app
python3.9 -m venv env --prompt="escriptorium"
source env/bin/activate
```

Install requirements
```sh
python -m pip install --upgrade pip
pip install wheel
pip install numpy
pip install -r requirements.txt
pip install -r requirements-dev.txt
```