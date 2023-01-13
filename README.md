# WebSPS

WebSPS is a Flask based web app designed to provide access to utilities for the Super-Enge Split-Pole Spectrograph at FSU. WebSPS currently uses a full-stack Flask framework with TailwindCSS and an SQLite database. It is intended to be a living repository of SPS tools, which will also provide students with an opprotunity to learn some python and web based development.

## Installation

To download the repository from github use `git clone https://github.com/gwm17/websps.git`. The first step is to install all of the python dependencies using pip. It is recommended to create a virtual environment to hold all of the packages. Virtual environments can be made with python using the following command: `python3 -m venv <your environment name>`. This will make a local directory named `<your environment name>` to hold all of the environment packages. On Linux you can activate the environment using `source /path/to/your/environment/bin/activate`. Once you've activated your environment you can install the required packages with pip using `pip install -r requirements.txt`.

Next, TailwindCSS needs to be installed and built. This is handled using the npm package manager, which is typically installed as part of the node.js package. Once you've installed node.js, move to the `static` folder of the WebSPS repository and run `npm install`. This will install all required node packages for tailwind. You can then compile the default tailwind config using `npx tailwindcss -i src/input.css -o dist/output.css`. If you're using this as production you may also want to add the `--minify` flag to the command to reduce the size of the generated css file. Note that the output file name and path is important, these are sourced in the html templates.

Now that all of the pre-requisites are installed, one needs to do some initial configuration of Flask. Most important is setting the `SECRET_KEY` and `ADMIN_PASSWORD`. These are both set in the `websps/__init__.py` file. `SECRET_KEY` should be a long random string of bytes or characters. The easiest way to make a secret key is to run the following command in the terminal: `python3 -c 'import secrets; print(secrets.token_hex())'`. This will print out a long random string of characters, which you can copy and paste into the file. The admin password should be a normal password known only to administrators of WebSPS. Administrators will have the ability to remove user accounts as well as clear user data. They cannot view user passwords or any other private information. Finally, once these values are set the SQLite database needs to be initialized. This can be done using the following command: `flask --app websps init-db`. This should be run from the top level of the repository, and the environment for which Flask has been installed must be active.

As a final step, if the app is to be run on an Apache2 server using mod_wsgi, some modifications to the wsgi.py file need to be made. The `PROJECT_DIR` variable in wsgi.py should be set to the full path to the installation of websps. This will ensure that when mod_wsgi sources this file, WebSPS will be in the python path.

Some other configuring may be necessary, but this varies server to server.

When developing, one can simply use the built-in flask development server to test by using the command: `flask --app websps --debug run`. Only ever use this for development.

## Requirements

- python >= 3.8
- node.js >= 18.13
