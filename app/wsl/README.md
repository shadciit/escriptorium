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
sudo apt install libxml2-dev libvips
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
yarn build
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

## Running the system outside Visual Studio Code
The database and redis are run inside docker:

    docker compose -f docker-compose-dev.yml up

To run the Django management script, you first need to make sure the proper settings file is used, do it by running

    export  DJANGO_SETTINGS_MODULE=escriptorium.wsl_dev_settings
    python manage.py runserver

If you want to develop the Vue frontend, you will need to run

    yarn start


## Working with Visual Studio Code
Visual Studio Code works inside WSL quite well. To get started, switch to the escriptorium directory and run

    code .

Visual Studio Code will download the necessary components and will start with the normal Windows UI.

There is a launch configration for the Backend, which can be run with F5. You can also run the frontend's watch script by choosing Terminal, Run Task, npm: start - front.

## Some notes to be moved to a different document

* scikit-learn upgraded from 0.19.2 to 1.0.2, since 0.19.2 won't install on Python 3.9. This causes a warning from coremltools, which is used by kraken. This warning is benign and can be ignored.
* psycopg2-binary needs to be older than 2.9, due to a conflict with Django 2.2. When we upgrade to Django 3 or 4, we can upgrade psycopg2
* Note that psycopg2-binary is not recommended for production use, for security reasons (it comes with its own libssl that is not upgraded by OS updates). It is recommended to compile psycopg2