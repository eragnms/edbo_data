Authentication
==============

Netatmo
-------
When running for the first time:

- Create a tokens.json file in the folder edbo_data/authentication/netatmo::

    touch tokens.json

- Add tokens.json to the file .gitignore
- Tighten the security for token.json::

    chmod 600 tokens.json

- Log in to your Netatmo account at `Netatmo <https://www.netatmo.com/>`_,
  navigate to collaborations, learn more and click your profile name and my
  apps. Now register an application and take notes of the cliend ID and client
  security (to be used in the next step).
- Configure the following environemnt variables::

    set -x NETATMO_CLIENT_ID <client_id>
    set -x NETATMO_CLIENT_SECRET <client_secret>
    set -x REDIRECT_URI http://localhost:5000/callback

- Install redis server::

    sudo pacman -S redis

- Start redis server in a separate terminal::

    redis-server

- In the folder edbo_data/authentication/netatmo run::

    python app.py

- In a browser navigate to http://localhost:5000
