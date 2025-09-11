
Tutorial
========

.. contents::
   :local:
   :depth: 2

1. Setup database, AI, and API server
-------------------------------------

   
| Please complete this step using our another repository (https://github.com/yuakagi/Watcher).
| Prepare your clinical record database (PostgreSQL) and the simulator AI (Watcher).
| Finally, launch the simulator API server (gunicorn + Flask) using Watcher.
| Tutorial is available at `Watcher documentation <https://yuakagi.github.io/Watcher/tutorial.html>`_.
   
2. Clone repository and configure .env
--------------------------------------

2-1. Clone repository
^^^^^^^^^^^^^^^^^^^^^^^

   .. code-block:: bash

      cd /path/to/your/working_dir
      git clone https://github.com/yuakagi/TwinEHR

2-2. Configure .env file
^^^^^^^^^^^^^^^^^^^^^^^^

| There is a file named `.env.example` in the root directory.
| Please **rename this file to .env** and configure the parameters in it.

| First, you need to generate Django's secret key.
| Run the following command in your terminal:

   .. code-block:: bash

      python -m venv .venv
      source .venv/bin/activate
      pip install django==5.1.7 
      python -c 'from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())'

| This will print random 50 characters in your terminal. This is the Django's secret key.
| Please **copy and paste this in SECRET_KEY** in the .env file.

| Then, remove .venv

   .. code-block:: bash

      deactivate
      rm -rf .venv

| Finally, configure other parameters in the .env file.

3. Initialize EHR site
-------------------------

3-1. Run docker compose
^^^^^^^^^^^^^^^^^^^^^^^^^

   .. code-block:: bash

      cd /path/to/your/working_dir
      docker compose up -d

| This will create a Docker container for the Django web server and PostgreSQL database.
| Then, it will also automatically run your django server inside the container.

3-2. Create a superuser
^^^^^^^^^^^^^^^^^^^^^^^^^

   .. code-block:: bash

      docker exec -it twinehr-django_web python3 manage.py createsuperuser

| Launches an interactive shell inside the container to create a Django superuser.
| You need email address etc to create the superuser, however, all of them can be dummy values.
| You do not have to use real personal information.
| (When prompted, choose gender from: F (Female), M (Male), O (Other).
| Enter your date-of-birth in the format YYYYMMDD.)

3. Use TwinEHR
--------------

| Open a web browser (e.g., Chrome or Safari).
| Then, navigate to: http://${HOST}:${DJANGO_PORT}
| HOST and DJANGO_PORT are defined in your .env file.
| For example, if HOST=123.45.67.1 and DJANGO_PORT=63435, the URL will be http://123.45.67.1:63435.