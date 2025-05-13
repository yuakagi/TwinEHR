
Tutorial
========

.. contents::
   :local:
   :depth: 2

1. Setup database, AI, and API server
-------------------------------------

   Please complete this step using our another repository (https://github.com/yuakagi/Watcher).
   Prepare your clinical record database (PostgreSQL) and the simulator AI (Watcher).
   Finally, launch the simulator API server (gunicorn + Flask) using Watcher.
   
2. Clone repository and configure .env
--------------------------------------

   Steps:

      1. Clone repository

         .. code-block:: bash

            cd /path/to/your/working_dir
            git clone https://github.com/yuakagi/TwinEHR

      3. Configure .env file

         There is a file named `.env.example` in the root directory.
         Please **rename this file to .env** and configure the parameters in it.

         First, you need to generate Django's secret key.
         Run the following command in your terminal:

         .. code-block:: bash

            python -m venv .venv
            source .venv/bin/activate
            pip install django==5.1.7 
            python -c 'from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())'

         This will print random 50 characters in your terminal. This is the Django's secret key.
         Please **copy and paste this in SECRET_KEY** in the .env file.

         Then, remove .venv

         .. code-block:: bash

            deactivate
            rm -rf .venv

         Finally, configure other parameters in the .env file.

2. Initialize Django site
-------------------------

   Steps:

      1. Run docker compose

         .. code-block:: bash

            cd /path/to/your/working_dir
            docker compose up -d

         This will create a Docker container for the Django web server and PostgreSQL database.
         Then, it will also automatically run your django server inside the container.

      2. Create a superuser

         .. code-block:: bash

            docker exec -it twinehr-django_web-1 python3 manage.py createsuperuser

         Launches an interactive shell inside the container to create a Django superuser.
         (When prompted, choose gender from: F (Female), M (Male), O (Other).)


3. Use TwinEHR
--------------

   Open a web browser (e.g., Chrome or Safari).
   Then, navigate to: http://${HOST}:${DJANGO_PORT}

   HOST and DJANGO_PORT are defined in your .env file.
   For example, if HOST=123.45.67.01 and DJANGO_PORT=63435, the URL will be http://123.45.67.01:63435.